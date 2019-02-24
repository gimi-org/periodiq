from datetime import datetime


def test_minutely():
    # * * * * *
    from periodiq import CronSpec

    spec = CronSpec(
        m=list(range(0, 60)),
        h=list(range(0, 24)),
        dom=list(range(1, 32)),
        month=list(range(1, 13)),
        dow=list(range(0, 7)),
    )

    s = spec.next_valid_date(datetime(2019, 6, 15, 12, 24, 30))
    assert s == datetime(2019, 6, 15, 12, 25)


def test_hourly():
    # 30 * * * *
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=list(range(0, 24)),
        dom=list(range(1, 32)),
        month=list(range(1, 13)),
        dow=list(range(0, 7)),
    )

    s = spec.next_valid_date(datetime(2019, 6, 15, 12, 24, 30))
    assert s == datetime(2019, 6, 15, 12, 30)

    s = spec.next_valid_date(datetime(2019, 6, 15, 12, 44))
    assert s == datetime(2019, 6, 15, 13, 30)


def test_daily():
    # 30 18 * * *
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=list(range(1, 32)),
        month=list(range(1, 13)),
        dow=list(range(0, 7)),
    )

    s = spec.next_valid_date(datetime(2019, 6, 15, 12, 24, 30))
    assert s == datetime(2019, 6, 15, 18, 30)

    s = spec.next_valid_date(datetime(2019, 6, 15, 19, 44))
    assert s == datetime(2019, 6, 16, 18, 30)


def test_weekly():
    # 30 18 * * Thu
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=list(range(1, 32)),
        month=list(range(1, 13)),
        dow=[4],
    )

    # A monday.
    d = datetime(2019, 2, 18, 12, 24, 30)
    assert 1 == d.isoweekday()
    s = spec.next_valid_date(d)
    # Task should run Thursday the 21st
    assert s == datetime(2019, 2, 21, 18, 30)

    # A saturday
    d = datetime(2019, 2, 23, 19, 44)
    assert 6 == d.isoweekday()
    s = spec.next_valid_date(d)
    # Task should run Thursday the 28th.
    assert s == datetime(2019, 2, 28, 18, 30)


def test_monthly():
    # 30 18 15 * *
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=[15],
        month=list(range(1, 13)),
        dow=list(range(0, 7)),
    )

    # This month
    d = datetime(2019, 2, 10, 12, 24, 30)
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 2, 15, 18, 30)

    # Next month
    d = datetime(2019, 2, 23, 19, 44)
    assert 6 == d.isoweekday()
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 3, 15, 18, 30)

    # Next year
    d = datetime(2019, 12, 23, 19, 44)
    s = spec.next_valid_date(d)
    assert s == datetime(2020, 1, 15, 18, 30)

    # 31st of each month: 30 18 31 * *
    spec = spec.replace(dom=[31])
    # Skip February
    d = datetime(2019, 2, 18, 12, 24, 30)
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 3, 31, 18, 30)


def test_mixed_weekly_monthly():
    # 30 18 15 * Thu
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=[15],
        month=list(range(1, 13)),
        dow=[4],
    )

    # Sun 10, Thu 14, Fri 15. -> schedule Thu.
    d = datetime(2019, 2, 10, 12, 24, 30)
    assert 7 == d.isoweekday()
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 2, 14, 18, 30)

    # Sun 13, Tue 15, Thu 17 - schedule Tue.
    d = datetime(2019, 1, 13, 19, 44)
    assert 7 == d.isoweekday()
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 1, 15, 18, 30)


def test_yearly():
    # 30 18 15 1 *
    from periodiq import CronSpec

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=[15],
        month=[6],
        dow=list(range(0, 7)),
    )

    # This year
    d = datetime(2019, 2, 10, 12, 24, 30)
    s = spec.next_valid_date(d)
    assert s == datetime(2019, 6, 15, 18, 30)

    # Next year
    d = datetime(2019, 12, 10, 12, 24, 30)
    s = spec.next_valid_date(d)
    assert s == datetime(2020, 6, 15, 18, 30)
