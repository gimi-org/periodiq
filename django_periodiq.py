import argparse
import importlib
import logging
import pdb
import sys
from copy import deepcopy
from calendar import monthrange
from datetime import timedelta
from pkg_resources import get_distribution
from queue import Queue

try:
    from signal import (
        SIGALRM,
        alarm,
        signal,
    )
except ImportError:
    SIGALARM = alarm = signal = None
from time import sleep

import pendulum

from dramatiq.middleware import SkipMessage
from django.core.management.base import OutputWrapper
import traceback
from dramatiq import Middleware
from dramatiq.cli import import_broker

stdout = OutputWrapper(sys.stdout)
logger = logging.getLogger('periodiq')


def cron(minute='*', hour='*', day_of_month='*', month='*', day_of_week='*'):
    return CronSpec.parse('{} {} {} {} {}'.format(minute, hour, day_of_month, month, day_of_week))


class CronSpec:
    _named_spec = {
        '@yearly': "0 0 1 1 *",
        '@annually': "0 0 1 1 *",
        '@monthly': "0 0 1 * *",
        '@weekly': "0 0 * * 0",
        '@daily': "0 0 * * *",
        '@midnight': "0 0 * * *",
        '@hourly': "0 * * * *",
    }

    @classmethod
    def parse(cls, spec):
        # Instanciate a CronSpec object from cron-like string.

        fields = spec.strip()
        if fields.startswith('@'):
            fields = cls._named_spec[fields]
        fields = fields.split()

        # Replace day of week by their number.
        day_of_week = fields[4].lower()
        weekdays = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
        for i, day in enumerate(weekdays):
            day_of_week = day_of_week.replace(day, str(i))

        return cls(
            minute=expand_valid(fields[0], min=0, max=59),
            hour=expand_valid(fields[1], min=0, max=23),
            day_of_month=expand_valid(fields[2], min=1, max=31),
            month=expand_valid(fields[3], min=1, max=12),
            day_of_week=expand_valid(day_of_week, min=0, max=7),
            parsed_from=spec,
        )

    def __init__(self,
                 minute,
                 hour,
                 day_of_month,
                 month,
                 day_of_week,
                 parsed_from=None):
        self.setup(minute=minute,
                   hour=hour,
                   day_of_month=day_of_month,
                   month=month,
                   day_of_week=day_of_week)
        self.parsed_from = parsed_from

    def __eq__(self, other):
        return self.astuple() == other.astuple()

    def __str__(self):
        if self.parsed_from is not None:
            return self.parsed_from
        else:
            return ' '.join([
                format_cron(self.minute, min_=0, max_=59),
                format_cron(self.hour, min_=0, max_=23),
                format_cron(self.day_of_month, min_=1, max_=31),
                format_cron(self.month, min_=1, max_=12),
                format_cron(self.day_of_week,
                            min_=0,
                            max_=7,
                            names=[
                                'Sun',
                                'Mon',
                                'Tue',
                                'Wed',
                                'Thu',
                                'Fri',
                                'Sat',
                                'Sun',
                            ]),
            ])

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)

    def astuple(self):
        return self.minute, self.hour, self.day_of_month, self.month, self.day_of_week

    def next_valid_date(self, last):
        # Note about DST. periodiq uses pendulum to have timezone-aware, always
        # valid date. For example, 2019-03-31T02:*:* does not exists in
        # timezone Europe/Paris. Using pendulum .add() methods never produces
        # invalid date. Also, pendulum.now() is always at right timezone.

        # Reset second and microsecond. It's irrelevant for scheduling.
        n = last.replace(second=0, microsecond=0)

        # Next date is at least in one minute.
        n = n.add(minutes=1)

        # How much minutes to way until next valid minute?
        delay_m = first(lambda x: x >= n.minute, self.minute_e) - n.minute
        n = n.add(minutes=delay_m)

        # How much hours to wait until next valid hour?
        delay_h = first(lambda x: x >= n.hour, self.hour_e) - n.hour
        n = n.add(hours=delay_h)

        # How much days to wait until next valid weekday?
        last_dow = n.isoweekday() % 7
        delay_dow = first(lambda x: x >= last_dow, self.dow_e) - last_dow

        # How much days to wait until next valid monthday?
        _, month_days = monthrange(n.year, n.month)
        # Drop irrelevant day of month (28+ or 31+) and adapt offset according
        # to current month.
        dom_e = [x for x in self.day_of_month if x <= month_days
                 ] + [month_days + self.day_of_month[0]]
        delay_dom = first(lambda x: x >= n.day, dom_e) - n.day

        if self.is_dow_restricted and self.is_dom_restricted:
            # Choose closest day matching day_of_month or day_of_week criteria
            delay_d = min(delay_dow, delay_dom)
        else:
            delay_d = delay_dow if self.is_dow_restricted else delay_dom

        n = n.add(days=delay_d)

        # How much days to wait until next valid month?
        next_month = first(lambda x: x >= n.month, self.month_e)
        delay_d = sum(monthesrange(n.year, n.month, next_month))
        n = n.add(days=delay_d)

        return n

    def replace(self,
                minute=None,
                hour=None,
                day_of_month=None,
                month=None,
                day_of_week=None):
        copy = deepcopy(self)
        copy.setup(minute=minute,
                   hour=hour,
                   day_of_month=day_of_month,
                   month=month,
                   day_of_week=day_of_week)
        return copy

    def setup(self, minute, hour, day_of_month, month, day_of_week):
        # For each field, we compute the next valid value out of bound. i.e if
        # valids minutes are [25, 50], appending 75 will ensure there is always
        # a next valid value for any minute between 0 and 59. timedelta will
        # ensure out of bound minutes are translated to next hour.
        if minute is not None:
            self.minute = minute
            self.minute_e = minute + [60 + minute[0]]
        if hour is not None:
            self.hour = hour
            self.hour_e = hour + [24 + hour[0]]
        if day_of_month is not None:
            self.is_dom_restricted = len(day_of_month) < 31
            self.day_of_month = day_of_month
        if month is not None:
            self.month = month
            self.month_e = month + [12 + month[0]]
        if day_of_week is not None:
            self.is_dow_restricted = len(day_of_week) < 7
            self.day_of_week = day_of_week
            self.dow_e = day_of_week + [7 + day_of_week[0]]
        # Invalidate string representation.
        self.parsed_from = None

    def validate(self, date):
        # Returns whether this date match the specified constraints.

        if date.minute not in self.minute:
            return False

        if date.hour not in self.hour:
            return False

        if date.month not in self.month:
            return False

        weekday = date.isoweekday()
        if self.is_dow_restricted and self.is_dom_restricted:
            if not (date.day in self.day_of_month
                    or weekday in self.day_of_week):
                return False
        else:
            if date.day not in self.day_of_month:
                return False
            if weekday not in self.day_of_week:
                return False

        return True


class PeriodiqMiddleware(Middleware):
    actor_options = set(['periodic'])

    def __init__(self, skip_delay=30):
        self.skip_delay = skip_delay

    def before_process_message(self, broker, message):
        actor = broker.actors[message.actor_name]
        if 'periodic' not in actor.options:
            return

        msg_str = '{}:{}'.format(message.message_id, message)
        if 'scheduled_at' not in message.options:
            stdout.write("{} looks manually triggered.".format(msg_str))
            return

        now = pendulum.now()
        scheduled_at = pendulum.parse(message.options['scheduled_at'])
        delta = now - scheduled_at

        if delta.total_seconds() > self.skip_delay:
            stdout.write("Skipping {} older than {}".format(
                msg_str, self.skip_delay))
            raise SkipMessage()
        else:
            stdout.write("Processing {} scheduled at {}.".format(
                msg_str, message.options['scheduled_at']))


class Scheduler:
    def __init__(self, actors):
        self.actors = actors
        # Q for communicating between main process and signal handler.
        self.alarm_q = Queue()

    def loop(self):
        # Block until signal handler sends True.
        while self.alarm_q.get(block=True):
            self.schedule()

    def send_actors(self, actors, now):
        now_str = str(now)
        for actor in actors:
            stdout.write("Scheduling {} at {}.".format(actor, now_str))
            actor.send_with_options(args=None, kwargs=None, delay=None, scheduled_at=now_str)

    def schedule(self):
        now = (pendulum.now() + timedelta(seconds=0.5)).replace(microsecond=0)
        stdout.write("Wake up at {}.".format(now))
        self.send_actors(
            [a for a in self.actors if a.options['periodic'].validate(now)],
            now=now)

        prioritized_actors = sorted(
            [(actor.options['periodic'].next_valid_date(now), actor)
             for actor in self.actors],
            key=lambda x: x[0])  # Sort only on date.

        next_date, _ = prioritized_actors[0]
        stdout.write("Nothing to do until {}.".format(next_date))
        # Refresh now because we may have spent some time sending messages.
        delay = next_date - pendulum.now()
        if delay.total_seconds() <= 0:
            stdout.write("Negative delay. Scheduling immediately.")
            return self.schedule()

        delay_s = delay.total_seconds()
        delay_s, delay_ms = int(delay_s), delay_s % 1
        stdout.write("Sleeping for {} ({}).".format(delay_s, delay))
        # Sleep microseconds because alarm only accepts integers.
        sleep(delay_ms)
        if delay_s:
            alarm(delay_s)
            signal(SIGALRM, self.signal_handler)
        else:
            self.alarm_q.put_nowait(True)

    def signal_handler(self, *_):
        stdout.write("Alaaaaarm!")
        self.alarm_q.put_nowait(True)


def expand_valid(value, min, max):
    # From cron-like time or date field, expand all valid values within min-max
    # interval.
    valid = set()
    value = value.replace('*', '{min}-{max}'.format(min=min, max=max))
    intervals = value.split(',')
    for interval in intervals:
        range_, _, step = interval.partition('/')
        step = 1 if '' == step else int(step)
        start, _, end = range_.partition('-')
        start = int(start)
        end = start if '' == end else int(end)
        # Note that step is not a modulo. cf.
        # https://stackoverflow.com/questions/27412483/how-do-cron-steps-work
        valid |= set(range(start, end + 1, step))
    return sorted(valid)


def first(function, iterable):
    # Return the first item from iterable accepted by function.
    try:
        return next(x for x in iterable if function(x))
    except StopIteration:
        raise ValueError("No matching value.")


def format_cron(values, min_, max_, names=None):
    if min_ == values[0] and values[-1] == max_:
        return '*'
    else:
        return ','.join(
            format_interval(*i, names=names) for i in group_intervals(values))


def format_interval(start, stop, names=None):
    if stop == start:
        return str(start if names is None else names[start])
    elif names:
        return ','.join(names[start:stop + 1])
    else:
        return '{}-{}'.format(start, stop)


def group_intervals(values):
    last = values[0]
    start = last
    for v in values[1:]:
        diff = v - last
        if diff > 1:
            yield start, last
            start = v
        last = v
    yield start, last


def monthesrange(start_year, start_month, end_month):
    # Switch to zero-base month numbering.
    start_month -= 1
    end_month -= 1
    return (x
            for _, x in (monthrange(start_year + minute // 12, 1 + minute % 12)
                         for minute in range(start_month, end_month)))


def make_argument_parser():
    dist = get_distribution('periodiq')
    parser = argparse.ArgumentParser(
        prog="periodiq",
        description="Run periodiq scheduler.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "broker",
        help="the broker to use (eg: 'module' or 'module:a_broker')",
    )

    parser.add_argument(
        "modules",
        metavar="module",
        nargs="*",
        help="additional python modules to import",
    )

    parser.add_argument(
        "--path",
        "-P",
        default=".",
        nargs="*",
        type=str,
        help="the module import path (default: %(default)s)",
    )

    parser.add_argument("--version", action="version", version=dist.version)
    parser.add_argument(
        "--verbose",
        "-v",
        default=0,
        action="count",
        help="turn on verbose log output",
    )

    return parser


def print_periodic_actors(actors):
    stdout.write("Registered periodic actors:")
    stdout.write("")
    stdout.write("    %-24s module:actor@queue" % ('m h dom month dow'))
    stdout.write("    %-24s ------------------" % ('-' * 24,))
    for actor in actors:
        kw = dict(
            module=actor.fn.__module__,
            name=actor.actor_name,
            queue=actor.queue_name,
            spec=str(actor.options['periodic']),
        )
        stdout.write("    %(spec)-24s %(module)s:%(name)s@%(queue)s " % kw)
    stdout.write("")


def entrypoint(schedule_module, broker='gimi', modules=[], verbose=logging.INFO, path='.'):
    try:
        exit(main(broker=broker, modules=modules, verbose=verbose, path=path, schedule_module=schedule_module))
    except (pdb.bdb.BdbQuit, KeyboardInterrupt):
        stdout.write("Interrupted.")
    except Exception as e:
        stdout.write('Unhandled error: {}, stack: {}'.format(
            e, traceback.format_exc()))
        stdout.write(
            "Please file an issue at "
            "https://gitlab.com/bersace/periodiq/issues/new with full log.", )
    exit(1)


def main(
        broker,
        modules,
        path,
        schedule_module,
        verbose=logging.DEBUG,
):
    logger.setLevel(verbose)
    if alarm is None:
        stdout.write("Unsupported system: alarm syscall is not available.")
        return 1

    stdout.write("Starting Django Periodiq, a simple scheduler for Django-Dramatiq.")

    for _path in path:
        sys.path.insert(0, _path)
    _, broker = import_broker(broker)
    for module in modules:
        importlib.import_module(module)

    actors_map = {actor.actor_name: actor for actor in broker.actors.values()}

    periodic_actors = set(
        actor for actor in broker.actors.values() if 'periodic' in actor.options
    )

    json_scheduler = importlib.import_module(schedule_module).schedule
    for task_name, task_cron_config in json_scheduler.items():
        task_name = task_cron_config['task'].split('.')[-1]
        task_schedule_cron = task_cron_config['schedule']

        try:
            _actor = actors_map[task_name]
            _actor.options['periodic'] = task_schedule_cron
            periodic_actors.add(actors_map[task_name])
        except KeyError:
            stdout.write('A task declared in the scheduler is missing from the app: {}'.format(task_name))

    if not periodic_actors:
        stdout.write("No periodic actor to schedule.")
        return 1

    print_periodic_actors(periodic_actors)

    scheduler = Scheduler(actors=periodic_actors)
    now = pendulum.now()
    # If we start late in a minute. Pad to start of next minute.
    if now.second > 55:
        stdout.write("Skipping to next minute.")
        sleep(60 - now.second)
    scheduler.schedule()
    scheduler.loop()

    return 0


if '__main__' == __name__:
    entrypoint()
