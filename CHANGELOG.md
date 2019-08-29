# Changelog

## Unreleased

- Print crontab on startup.


## 0.10.1

Released 2019 august 27th.

- Fix --help.


## 0.10.0

Released 2019 march 27th.

- Support Python 3.5.
- Always use timezone-aware dates with [pendulum](https://pendulum.eustace.io).

  No task should be scheduled on an inexistant date in a timezone. Note that
  some exotic time zones with DST other than 1h, like Australia/Lord_Howe, will
  have bug with tasks planified between 2h and 3h AM.


## 0.9.0

First usable release.

- SIGALRM-based scheduler.
- crontab format parsing.
- Unit test of date calculation.
