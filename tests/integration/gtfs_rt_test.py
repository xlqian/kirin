# Copyright (c) 2001-2017, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io
from datetime import timedelta
import datetime
import pytest
from pytz import utc
from kirin.core.model import RealTimeUpdate, db, TripUpdate, StopTimeUpdate
from kirin.core.populate_pb import to_posix_time, convert_to_gtfsrt
from kirin import gtfs_rt
from tests import mock_navitia
from tests.check_utils import dumb_nav_wrapper, api_post
from kirin import gtfs_realtime_pb2, app


@pytest.fixture(scope='function', autouse=True)
def navitia(monkeypatch):
    """
    Mock all calls to navitia for this fixture
    """
    monkeypatch.setattr('navitia_wrapper._NavitiaWrapper.query', mock_navitia.mock_navitia_query)


@pytest.fixture(scope='function')
def mock_rabbitmq(monkeypatch):
    """
    Mock all calls to navitia for this fixture
    """
    from mock import MagicMock
    mock_amqp = MagicMock()
    monkeypatch.setattr('kombu.messaging.Producer.publish', mock_amqp)
    return mock_amqp


@pytest.fixture()
def basic_gtfs_rt_data():
    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.gtfs_realtime_version = "1.0"
    feed.header.incrementality = gtfs_realtime_pb2.FeedHeader.FULL_DATASET
    feed.header.timestamp = to_posix_time(datetime.datetime(year=2012, month=6, day=15, hour=15))

    entity = feed.entity.add()
    entity.id = 'bob'
    trip_update = entity.trip_update
    trip_update.trip.trip_id = "Code-R-vj1"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 60
    stu.stop_sequence = 2
    stu.stop_id = "Code-StopR2"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 180
    stu.stop_sequence = 4
    stu.stop_id = "Code-StopR4"

    return feed


def test_wrong_gtfs_rt_post():
    """
    wrong protobuf post on the api
    """
    res, status = api_post('/gtfs_rt', check=False, data='bob')

    assert status == 400

    print res.get('error') == 'invalid'


def test_gtfs_rt_post_no_data():
    """
    when no data is given, we got a 400 error
    """
    tester = app.test_client()
    resp = tester.post('/gtfs_rt')
    assert resp.status_code == 400

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 0
        assert len(TripUpdate.query.all()) == 0
        assert len(StopTimeUpdate.query.all()) == 0


def test_gtfs_model_builder(basic_gtfs_rt_data):
    """
    test the model builder with a simple gtfs-rt

    we have realtime data on only 2 stops, so the model builder should only have 2 stops (even if the VJ
    have 4 stops)
    """
    with app.app_context():
        data = ''
        rt_update = RealTimeUpdate(data, connector='gtfs-rt', contributor='realtime.gtfs')
        trip_updates = gtfs_rt.KirinModelBuilder(dumb_nav_wrapper()).build(rt_update, basic_gtfs_rt_data)

        # we associate the trip_update manually for sqlalchemy to make the links
        rt_update.trip_updates = trip_updates
        db.session.add(rt_update)
        db.session.commit()

        assert len(trip_updates) == 1
        assert len(trip_updates[0].stop_time_updates) == 2

        second_stop = trip_updates[0].stop_time_updates[0]
        assert second_stop.stop_id == 'StopR2'
        assert second_stop.arrival_status == 'update'
        assert second_stop.arrival_delay == timedelta(minutes=1)
        assert second_stop.departure_delay is None
        assert second_stop.departure_status == 'none'
        assert second_stop.message is None

        fourth_stop = trip_updates[0].stop_time_updates[1]
        assert fourth_stop.stop_id == 'StopR4'
        assert fourth_stop.arrival_status == 'update'
        assert fourth_stop.arrival_delay == timedelta(minutes=3)
        assert fourth_stop.departure_delay is None
        assert fourth_stop.departure_status == 'none'
        assert fourth_stop.message is None

        feed = convert_to_gtfsrt(trip_updates)
        assert feed.entity[0].trip_update.trip.start_date == u'20120615' #must be UTC start date


def test_gtfs_rt_simple_delay(basic_gtfs_rt_data, mock_rabbitmq):
    """
    test the gtfs-rt post with a simple gtfs-rt

    we have realtime data on only 2 stops, so the model builder should only have 2 stops (even if the VJ
    have 4 stops)

    after the merge, we should have 4 stops (and only 2 delayed)
    """
    tester = app.test_client()
    resp = tester.post('/gtfs_rt', data=basic_gtfs_rt_data.SerializeToString())
    assert resp.status_code == 200

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 4

        trip_update = TripUpdate.find_by_dated_vj('R:vj1', datetime.datetime(2012, 6, 15, 14, 0))

        assert trip_update

        # navitia's time are in local, but we return UTC time, and the stop is in sherbrooke, so UTC-4h
        first_stop = trip_update.stop_time_updates[0]
        assert first_stop.stop_id == 'StopR1'
        assert first_stop.arrival_status == 'none'
        assert first_stop.arrival_delay == timedelta(0)
        assert first_stop.arrival == datetime.datetime(2012, 6, 15, 14, 00)
        assert first_stop.departure_delay == timedelta(0)
        assert first_stop.departure_status == 'none'
        assert first_stop.departure == datetime.datetime(2012, 6, 15, 14, 00)
        assert first_stop.message is None

        second_stop = trip_update.stop_time_updates[1]
        assert second_stop.stop_id == 'StopR2'
        assert second_stop.arrival_status == 'update'
        # 10:30 in local + 4h to get it in UTC + 1minute of delay
        assert second_stop.arrival == datetime.datetime(2012, 6, 15, 14, 31)
        assert second_stop.arrival_delay == timedelta(minutes=1)
        # even if the GTFS-RT has no information of the departure, it have been also delayed by 1mn
        # for coherence
        assert second_stop.departure == datetime.datetime(2012, 6, 15, 14, 31)
        assert second_stop.departure_delay == timedelta(minutes=1)
        assert second_stop.departure_status == 'none'
        assert second_stop.message is None

        third_stop = trip_update.stop_time_updates[2]
        assert third_stop.stop_id == 'StopR3'
        assert third_stop.arrival_status == 'none'
        assert third_stop.arrival_delay == timedelta(0)
        assert third_stop.arrival == datetime.datetime(2012, 6, 15, 15, 00)
        assert third_stop.departure_delay == timedelta(0)
        assert third_stop.departure_status == 'none'
        assert third_stop.departure == datetime.datetime(2012, 6, 15, 15, 00)
        assert third_stop.message is None

        fourth_stop = trip_update.stop_time_updates[3]
        assert fourth_stop.stop_id == 'StopR4'
        assert fourth_stop.arrival_status == 'update'
        assert fourth_stop.arrival_delay == timedelta(minutes=3)
        assert fourth_stop.arrival == datetime.datetime(2012, 6, 15, 15, 33)
        # even if the GTFS-RT has no information of the departure, it have been also delayed by 3mn
        # for coherence
        assert fourth_stop.departure_delay == timedelta(minutes=3)
        assert fourth_stop.departure_status == 'none'
        assert fourth_stop.departure == datetime.datetime(2012, 6, 15, 15, 33)
        assert fourth_stop.message is None


@pytest.fixture()
def pass_midnight_gtfs_rt_data():
    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.gtfs_realtime_version = "1.0"
    feed.header.incrementality = gtfs_realtime_pb2.FeedHeader.FULL_DATASET
    feed.header.timestamp = to_posix_time(datetime.datetime(year=2012, month=6, day=16, hour=5))

    entity = feed.entity.add()
    entity.id = 'bob'
    trip_update = entity.trip_update
    trip_update.trip.trip_id = "Code-pass-midnight"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 60
    stu.departure.delay = 60
    stu.stop_sequence = 1
    stu.stop_id = "Code-StopR1"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 120
    stu.departure.delay = 120
    stu.stop_sequence = 2
    stu.stop_id = "Code-StopR2"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 150
    stu.departure.delay = 150
    stu.stop_sequence = 3
    stu.stop_id = "Code-StopR2-bis"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 180
    stu.departure.delay = 180
    stu.stop_sequence = 4
    stu.stop_id = "Code-StopR3"

    stu = trip_update.stop_time_update.add()
    stu.arrival.delay = 240
    stu.departure.delay = 240
    stu.stop_sequence = 5
    stu.stop_id = "Code-StopR4"

    return feed


def test_gtfs_pass_midnight_model_builder(pass_midnight_gtfs_rt_data):
    """
    test the model builder with a pass-midnight gtfs-rt
    """
    with app.app_context():
        data = ''
        rt_update = RealTimeUpdate(data, connector='gtfs-rt', contributor='realtime.gtfs')
        trip_updates = gtfs_rt.KirinModelBuilder(dumb_nav_wrapper()).build(rt_update, pass_midnight_gtfs_rt_data)

        # we associate the trip_update manually for sqlalchemy to make the links
        rt_update.trip_updates = trip_updates
        db.session.add(rt_update)
        db.session.commit()

        assert len(trip_updates) == 1
        assert len(trip_updates[0].stop_time_updates) == 5

        first_stop = trip_updates[0].stop_time_updates[0]
        assert first_stop.stop_id == 'StopR1'
        assert first_stop.arrival_status == 'update'
        assert first_stop.arrival_delay == timedelta(minutes=1)
        assert first_stop.departure_status == 'update'
        assert first_stop.departure_delay == timedelta(minutes=1)
        assert first_stop.message is None

        second_stop = trip_updates[0].stop_time_updates[1]
        assert second_stop.stop_id == 'StopR2'
        assert second_stop.arrival_status == 'update'
        assert second_stop.arrival_delay == timedelta(minutes=2)
        assert second_stop.departure_status == 'update'
        assert second_stop.departure_delay == timedelta(minutes=2)
        assert second_stop.message is None

        second_stop = trip_updates[0].stop_time_updates[2]
        assert second_stop.stop_id == 'StopR2-bis'
        assert second_stop.arrival_status == 'update'
        assert second_stop.arrival_delay == timedelta(minutes=2, seconds=30)
        assert second_stop.departure_status == 'update'
        assert second_stop.departure_delay == timedelta(minutes=2, seconds=30)
        assert second_stop.message is None

        third_stop = trip_updates[0].stop_time_updates[3]
        assert third_stop.stop_id == 'StopR3'
        assert third_stop.arrival_status == 'update'
        assert third_stop.arrival_delay == timedelta(minutes=3)
        assert third_stop.departure_status == 'update'
        assert third_stop.departure_delay == timedelta(minutes=3)
        assert third_stop.message is None

        fourth_stop = trip_updates[0].stop_time_updates[4]
        assert fourth_stop.stop_id == 'StopR4'
        assert fourth_stop.arrival_status == 'update'
        assert fourth_stop.arrival_delay == timedelta(minutes=4)
        assert fourth_stop.departure_status == 'update'
        assert fourth_stop.departure_delay == timedelta(minutes=4)
        assert fourth_stop.message is None

        feed = convert_to_gtfsrt(trip_updates)
        assert feed.entity[0].trip_update.trip.start_date == u'20120616' #must be UTC start date


def test_gtfs_rt_pass_midnight(pass_midnight_gtfs_rt_data, mock_rabbitmq):
    """
    test the gtfs-rt post with a pass-midnight gtfs-rt

    we have realtime data on only the 4 stops

    after the merge, we should have 4 stops properly delayed
    """
    tester = app.test_client()
    resp = tester.post('/gtfs_rt', data=pass_midnight_gtfs_rt_data.SerializeToString())
    assert resp.status_code == 200

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 5

        trip_update = TripUpdate.find_by_dated_vj('R:vj1', datetime.datetime(2012, 6, 16, 3, 30))

        assert trip_update

        assert trip_update.vj.get_start_timestamp() == datetime.datetime(2012, 6, 16, 3, 30, tzinfo=utc)

        # navitia's time are in local, but we return UTC time, and the stop is in sherbrooke, so UTC-4h
        first_stop = trip_update.stop_time_updates[0]
        assert first_stop.stop_id == 'StopR1'
        assert first_stop.arrival_status == 'update'
        assert first_stop.arrival_delay == timedelta(minutes=1)
        # 23:30 in local + 4h to get it in UTC + 1minute of delay
        assert first_stop.arrival == datetime.datetime(2012, 6, 16, 03, 31)
        assert first_stop.departure_delay == timedelta(minutes=1)
        assert first_stop.departure_status == 'update'
        assert first_stop.departure == datetime.datetime(2012, 6, 16, 03, 31)
        assert first_stop.message is None

        second_stop = trip_update.stop_time_updates[1]
        assert second_stop.stop_id == 'StopR2'
        assert second_stop.arrival_status == 'update'
        assert second_stop.arrival == datetime.datetime(2012, 6, 16, 04, 01)
        assert second_stop.arrival_delay == timedelta(minutes=2)
        assert second_stop.departure == datetime.datetime(2012, 6, 16, 04, 02)
        assert second_stop.departure_delay == timedelta(minutes=2)
        assert second_stop.departure_status == 'update'
        assert second_stop.message is None

        second_stop = trip_update.stop_time_updates[2]
        assert second_stop.stop_id == 'StopR2-bis'
        assert second_stop.arrival_status == 'update'
        assert second_stop.arrival == datetime.datetime(2012, 6, 16, 04, 02, 30)
        assert second_stop.arrival_delay == timedelta(minutes=2, seconds=30)
        assert second_stop.departure == datetime.datetime(2012, 6, 16, 04, 02, 30)
        assert second_stop.departure_delay == timedelta(minutes=2, seconds=30)
        assert second_stop.departure_status == 'update'
        assert second_stop.message is None

        third_stop = trip_update.stop_time_updates[3]
        assert third_stop.stop_id == 'StopR3'
        assert third_stop.arrival_status == 'update'
        assert third_stop.arrival_delay == timedelta(minutes=3)
        assert third_stop.arrival == datetime.datetime(2012, 6, 16, 04, 03)
        assert third_stop.departure_delay == timedelta(minutes=3)
        assert third_stop.departure_status == 'update'
        assert third_stop.departure == datetime.datetime(2012, 6, 16, 04, 04)
        assert third_stop.message is None

        fourth_stop = trip_update.stop_time_updates[4]
        assert fourth_stop.stop_id == 'StopR4'
        assert fourth_stop.arrival_status == 'update'
        assert fourth_stop.arrival_delay == timedelta(minutes=4)
        assert fourth_stop.arrival == datetime.datetime(2012, 6, 16, 04, 34)
        assert fourth_stop.departure_delay == timedelta(minutes=4)
        assert fourth_stop.departure_status == 'update'
        assert fourth_stop.departure == datetime.datetime(2012, 6, 16, 04, 34)
        assert fourth_stop.message is None
