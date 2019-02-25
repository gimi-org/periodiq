import argparse
import importlib
import logging
import pdb
import sys
from copy import deepcopy
from calendar import monthrange
from datetime import (
    datetime,
    timedelta,
)
from pkg_resources import get_distribution
from queue import SimpleQueue
from signal import (
    SIGALRM,
    alarm,
    signal,
)
from time import sleep

from dramatiq import Middleware
from dramatiq.cli import (
    LOGFORMAT,
    VERBOSITY,
    import_broker,
)


logger = logging.getLogger('periodiq')


def cron(spec):
    return CronSpec.parse(spec)


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
        dow = fields[4].lower()
        weekdays = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
        for i, day in enumerate(weekdays):
            dow = dow.replace(day, f'{i}')

        return cls(
            m=expand_valid(fields[0], min=0, max=59),
            h=expand_valid(fields[1], min=0, max=23),
            dom=expand_valid(fields[2], min=1, max=31),
            month=expand_valid(fields[3], min=1, max=12),
            dow=expand_valid(dow, min=0, max=7),
        )

    def __init__(self, m, h, dom, month, dow):
        self.setup(m, h, dom, month, dow)

    def __eq__(self, other):
        return self.astuple() == other.astuple()

    def astuple(self):
        return self.minute, self.hour, self.dom, self.month, self.dow

    def next_valid_date(self, last):
        # Reset second and microsecond. It's irrelevant for scheduling.
        n = last.replace(second=0, microsecond=0)

        # Next date is at least in one minute.
        n += timedelta(minutes=1)

        # How much minutes to way until next valid minute?
        delay_m = first(lambda x: x >= n.minute, self.minute_e) - n.minute
        n += timedelta(minutes=delay_m)

        # How much hours to wait until next valid hour?
        delay_h = first(lambda x: x >= n.hour, self.hour_e) - n.hour
        n += timedelta(hours=delay_h)

        # How much days to wait until next valid weekday?
        last_dow = n.isoweekday() % 7
        delay_dow = first(lambda x: x >= last_dow, self.dow_e) - last_dow

        # How much days to wait until next valid monthday?
        _, month_days = monthrange(n.year, n.month)
        # Drop irrelevant day of month (28+ or 31+) and adapt offset according
        # to current month.
        dom_e = [
            x for x in self.dom if x <= month_days
        ] + [
            month_days + x for x in self.dom
        ]
        delay_dom = first(lambda x: x >= n.day, dom_e) - n.day

        if self.is_dow_restricted and self.is_dom_restricted:
            # Choose closest day matching dom or dow criteria
            delay_d = min(delay_dow, delay_dom)
        else:
            delay_d = delay_dow if self.is_dow_restricted else delay_dom

        n += timedelta(days=delay_d)

        # How much days to wait until next valid month?
        next_month = first(lambda x: x >= n.month, self.month_e)
        delay_d = sum(monthesrange(n.year, n.month, next_month))
        n += timedelta(days=delay_d)

        return n

    def replace(self, m=None, h=None, dom=None, month=None, dow=None):
        copy = deepcopy(self)
        copy.setup(m, h, dom, month, dow)
        return copy

    def setup(self, m, h, dom, month, dow):
        # For each field, we compute the next valid value out of bound. i.e if
        # valids minutes are [25, 50], appending 75 will ensure there is always
        # a next valid value for any minute between 0 and 59. timedelta will
        # ensure out of bound minutes are translated to next hour.
        if m is not None:
            self.minute = m
            self.minute_e = m + [60 + m[0]]
        if h is not None:
            self.hour = h
            self.hour_e = h + [24 + h[0]]
        if dom is not None:
            self.is_dom_restricted = len(dom) < 31
            self.dom = dom
        if month is not None:
            self.month = month
            self.month_e = month + [12 + month[0]]
        if dow is not None:
            self.is_dow_restricted = len(dow) < 7
            self.dow = dow
            self.dow_e = dow + [7 + dow[0]]

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
            if not (date.day in self.dom or weekday in self.dow):
                return False
        else:
            if date.day not in self.dom:
                return False
            if weekday not in self.dow:
                return False

        return True


def entrypoint():
    logging.basicConfig(level=logging.INFO, format=LOGFORMAT)

    try:
        exit(main())
    except (pdb.bdb.BdbQuit, KeyboardInterrupt):
        logger.info("Interrupted.")
    except Exception:
        logger.exception('Unhandled error:')
        logger.error(
            "Please file an issue at "
            "https://gitlab.com/bersace/periodiq/issues/new with full log.",
        )
    exit(1)


def expand_valid(value, min, max):
    # From cron-like time or date field, expand all valid values within min-max
    # interval.
    valid = set()
    value = value.replace('*', f'{min}-{max}')
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


def monthesrange(start_year, start_month, end_month):
    # Switch to zero-base month numbering.
    start_month -= 1
    end_month -= 1
    return (
        x for _, x in (
            monthrange(start_year + m // 12, 1 + m % 12)
            for m in range(start_month, end_month)
        )
    )


def main():
    parser = make_argument_parser()
    args = parser.parse_args()

    logging.getLogger().setLevel(VERBOSITY.get(args.verbose, logging.DEBUG))

    for path in args.path:
        sys.path.insert(0, path)
    _, broker = import_broker(args.broker)
    for module in args.modules:
        importlib.import_module(module)

    periodic_actors = [
        a for a in broker.actors.values()
        if 'periodic' in a.options
    ]
    if not periodic_actors:
        logger.error("No periodic actor to schedule.")
        return 1

    scheduler = Scheduler(actors=periodic_actors)
    now = datetime.now()
    # If we start late in a minute. Pad to start of next minute.
    if now.second > 55:
        logger.debug("Skipping to next minute.")
        sleep(60 - now.second)
    scheduler.schedule()
    scheduler.loop()

    return 0


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
        "modules", metavar="module", nargs="*",
        help="additional python modules to import",
    )

    parser.add_argument(
        "--path", "-P", default=".", nargs="*", type=str,
        help="the module import path (default: %default)",
    )

    parser.add_argument("--version", action="version", version=dist.version)
    parser.add_argument(
        "--verbose", "-v", default=0, action="count",
        help="turn on verbose log output",
    )

    return parser


class PeriodiqMiddleware(Middleware):
    actor_options = set(['periodic'])


class Scheduler:
    def __init__(self, actors):
        self.actors = actors
        # Q for communicating between main process and signal handler.
        self.alarm_q = SimpleQueue()

    def loop(self):
        # Block until signal handler sends True.
        while self.alarm_q.get(block=True):
            self.schedule()

    def send_actors(self, actors):
        for actor in actors:
            logger.info("Scheduling %s.", actor)
            actor.send()

    def schedule(self):
        now = datetime.now()
        logger.debug("Wake up at %s.", now)
        self.send_actors([
            a for a in self.actors
            if a.options['periodic'].validate(now)
        ])

        prioritized_actors = sorted([
            (actor.options['periodic'].next_valid_date(now), actor)
            for actor in self.actors
        ], key=lambda x: x[0])  # Sort only on date.

        next_date, _ = prioritized_actors[0]
        logger.debug("Nothing to do until %s.", next_date)
        delay = next_date - now
        delay_s = delay.total_seconds()
        delay_s, delay_ms = int(delay_s), delay_s % 1
        logger.debug("Sleeping for %ss (%s).", delay_s, delay)
        # Sleep microseconds because alarm only accepts integers.
        sleep(delay_ms)
        if delay_s:
            alarm(delay_s)
            signal(SIGALRM, self.signal_handler)
        else:
            self.alarm_q.put_nowait(True)

    def signal_handler(self, *_):
        logger.debug("Alaaaaarm!")
        self.alarm_q.put_nowait(True)


if '__main__' == __name__:
    entrypoint()
