import logging
from datetime import datetime

import dramatiq
from dramatiq.brokers.stub import StubBroker
from django_periodiq import cron, PeriodiqMiddleware


broker = StubBroker()
broker.add_middleware(PeriodiqMiddleware())
dramatiq.set_broker(broker)
logger = logging.getLogger(__name__)
now = datetime.now()


@dramatiq.actor(periodic=cron('* * * * *'))
def minutely():
    logger.info("Minutely.")


@dramatiq.actor(periodic=cron('*/15 * * * *'))
def quarthourly():
    logger.info("Quart-hourly.")


@dramatiq.actor(periodic=cron('@hourly'))
def hourly():
    logger.info("Hourly.")


@dramatiq.actor(periodic=cron('1 2 * * *'))
def dst():
    logger.info("Skipped on daylight saving time change in Europe/Paris.")


# For testing purpose, schedule daily in current hour.
@dramatiq.actor(periodic=cron('58 {} * * *'.format(now.hour)))
def daily():
    logger.info("Daily.")


@dramatiq.actor(periodic=cron('30 10 * * Sun'))
def weekly():
    logger.info("Ding dong ding dong!")


@dramatiq.actor(periodic=cron('0 18 1 * *'))
def monthly():
    logger.info("Income day.")


@dramatiq.actor(periodic=cron('0 0 25 12 *'))
def yearly():
    logger.info("Merry Chrismas!")


@dramatiq.actor()
def notperiodic():
    raise Exception("Must not be schedule.")
