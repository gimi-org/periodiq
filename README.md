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
- Skip outdated message.


## Installation

periodiq is licensed under LGPL 3.0+.

``` console
$ pip install periodiq
```

Declare periodic tasks like this:

``` python
# filename: app.py

import dramatiq
from periodiq import PeriodiqMiddleWare, cron

broker.add_middleware(PeriodiqMiddleWare(skip_delay=30))

@dramatiq.actor(periodic=cron('0 * * * *))
def hourly():
    # Do something each hour…
    ...
```

Then, run scheduler with:

``` console
$ periodiq -v app
[INFO] Starting Periodiq, a simple scheduler for Dramatiq.
[INFO] Registered periodic actors:
[INFO]
[INFO]     m h dom mon dow          module:actor@queue
[INFO]     ------------------------ ------------------
[INFO]     0 * * * *                app:hourly@default
[INFO]
...
```


## Support

If you need help or found a bug, mind [opening a GitLab
issue](https://gitlab.com/bersace/periodiq/issues/new) on the project. French
and English spoken.
