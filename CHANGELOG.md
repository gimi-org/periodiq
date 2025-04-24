# Changelog

## 0.13.0 — Released April 2025
- Added compatibility with Python 3.12
- Updated Pendulum version support to >=2.1,<4.0
- Updated to new django version


## 0.12.0

Released 2019 november 7h.

- Print crontab on startup.
- Skip outdated messages.
- Don't require alarm syscall to declare periodic tasks. Reported by
  @sovetnikov.
- Reschedule immediatly if schedule loop last after next tasks date. Reported by
  @sovetnikov.


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
