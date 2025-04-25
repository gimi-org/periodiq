from pendulum import datetime

from periodiq import CronSpec, cron, format_interval, group_intervals


def test_parse():
    spec = cron('* * * * *')
    assert list(range(0, 60)) == spec.minute
    assert list(range(0, 24)) == spec.hour
    assert list(range(1, 32)) == spec.dom
    assert list(range(1, 13)) == spec.month
    assert list(range(0, 8)) == spec.dow

    spec = cron('1,5-10 10-20/2,1 1,2,3,5,8,13,21 */5 mon,thu')
    assert [1, 5, 6, 7, 8, 9, 10] == spec.minute
    assert [1, 10, 12, 14, 16, 18, 20] == spec.hour
    assert [1, 2, 3, 5, 8, 13, 21] == spec.dom
    assert [1, 6, 11] == spec.month
    assert [1, 4] == spec.dow

    assert cron("0 0 1 1 *") == cron('@yearly')
    assert cron("0 0 1 1 *") == cron('@annually')
    assert cron("0 0 1 * *") == cron('@monthly')
    assert cron("0 0 * * 0") == cron('@weekly')
    assert cron("0 0 * * *") == cron('@daily')
    assert cron("0 0 * * *") == cron('@midnight')
    assert cron("0 * * * *") == cron('@hourly')


def test_minutely():
    # * * * * *

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


def test_validate():

    spec = CronSpec(
        m=[30],
        h=[18],
        dom=[15],
        month=list(range(1, 13)),
        dow=[4],
    )

    assert spec.validate(datetime(2019, 1, 15, 18, 30))
    assert not spec.validate(datetime(2019, 1, 16, 18, 30))
    assert spec.validate(datetime(2019, 1, 17, 18, 30))


def test_dst_change():

    d = datetime(2019, 3, 31, 1, 57, 30, tz='Europe/Paris')
    s = cron('1 2 * * *').next_valid_date(d)
    # There is no 2019-03-31T02:01 CET. Skip to April fool. <°)))><
    assert datetime(2019, 4, 1, 2, 1, tz='Europe/Paris') == s


def test_format():

    minutely = cron('* * * * *')
    assert '* * * * *' == str(minutely)
    assert minutely == cron(str(minutely))

    spec = minutely.replace(m=[0])
    assert '0 * * * *' == str(spec)
    assert spec == cron(str(spec))

    spec = minutely.replace(m=[0, 1, 2, 3, 10, 11, 12, 13])
    assert '0-3,10-13 * * * *' == str(spec)
    assert spec == cron(str(spec))

    spec = minutely.replace(dow=[0, 1, 3])
    assert '* * * * Sun,Mon,Wed' == str(spec)
    assert spec == cron(str(spec))


def test_group_intervals():

    res = list(group_intervals([0, 2, 5]))
    wanted = [(0, 0), (2, 2), (5, 5)]
    assert wanted == res

    res = list(group_intervals([0, 1, 2, 3, 5, 7, 8]))
    wanted = [(0, 3), (5, 5), (7, 8)]
    assert wanted == res


def test_format_interval():

    assert '0' == format_interval(start=0, stop=0)
    assert '1-2' == format_interval(start=1, stop=2)
    assert 'Sun,Mon' == format_interval(0, 1, names=['Sun', 'Mon', 'Tue'])
