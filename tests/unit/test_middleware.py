from pendulum import datetime

import pytest
from dramatiq.brokers.stub import StubBroker
from dramatiq import actor

from django_periodiq import cron, PeriodiqMiddleware


broker = StubBroker()
middleware = PeriodiqMiddleware()
broker.add_middleware(middleware)


@actor(broker=broker, periodic=cron('* * * * *'))
def periodic_actor():
    pass


@actor(broker=broker)
def regular_actor():
    pass


def test_skip_outdated(mocker):
    from django_periodiq import SkipMessage

    message = periodic_actor.message_with_options(
        scheduled_at=str(datetime(2019, 8, 29, 10, 54, 0)))
    now = mocker.patch('periodiq.pendulum.now')
    now.return_value = datetime(2019, 8, 29, 10, 54, middleware.skip_delay + 1)

    with pytest.raises(SkipMessage):
        middleware.before_process_message(broker, message)


def test_process_regular_message(mocker):
    message = regular_actor.message()
    middleware.before_process_message(broker, message)


def test_process_ontime_message(mocker):
    message = periodic_actor.message_with_options(
        scheduled_at=str(datetime(2019, 8, 29, 10, 54, 0)))
    now = mocker.patch('periodiq.pendulum.now')
    now.return_value = datetime(2019, 8, 29, 10, 54, 1)

    middleware.before_process_message(broker, message)
