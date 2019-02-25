# Simple Scheduler for Dramatiq Task Queue

[dramatiq](https://dramatiq.io) task queue is great but lake a scheduler. This
project fills the gap.


## Features

- Cron-like scheduling.
- Single process.
- Fast and simple implementation.
- Easy on ressources using SIGALRM.
- No dependency except dramatiq ones.
- CLI consistent with dramatiq.


## Installation

periodiq is licensed under LGPL 3.0+.

``` console
$ pip install periodiq
```

Declare periodic tasks like this:

``` python
import dramatiq
from periodiq import PeriodicMiddleWare, cron

broker.add_middleware(PeriodicMiddleWare())

@dramatiq.actor(periodic=cron('0 * * * *))
def hourly():
    # Do something each hour…
    ...
```

Then, run scheduler with:

``` console
$ periodiq -v my.broker.module
```


## Support

If you need help or found a bug, mind [opening a GitLab
issue](https://gitlab.com/bersace/periodiq/issues/new) on the project. French
and English spoken.
