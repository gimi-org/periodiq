from copy import deepcopy
from calendar import monthrange
from datetime import timedelta


def cron(spec):
    return CronSpec.parse(spec)


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


class CronSpec:
    def __init__(self, m, h, dom, month, dow):
        self.setup(m, h, dom, month, dow)

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


def main():
    return 0


def entrypoint():
    pass


if '__main__' == __name__:
    entrypoint()
