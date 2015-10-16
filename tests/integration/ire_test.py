# coding: utf8

# Copyright (c) 2001-2015, Canal TP and/or its affiliates. All rights reserved.
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

import pytest

from tests.check_utils import api_post
import datetime
from kirin import app
from tests import mock_navitia
from tests.check_utils import get_ire_data
from kirin.core.model import RealTimeUpdate, TripUpdate, VehicleJourney, StopTimeUpdate


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


def test_wrong_ire_post():
    """
    simple xml post on the api
    """
    res, status = api_post('/ire', check=False, data='<bob></bob>')

    assert status == 400

    print res.get('error') == 'invalid'


def test_ire_post_no_data():
    """
    when no data is given, we got a 400 error
    """
    tester = app.test_client()
    resp = tester.post('/ire')
    assert resp.status_code == 400

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 0
        assert len(TripUpdate.query.all()) == 0
        assert len(StopTimeUpdate.query.all()) == 0


def check_db_ire_96231_delayed():
    with app.app_context():
        assert len(RealTimeUpdate.query.all()) >= 1
        assert len(TripUpdate.query.all()) >= 1
        assert len(StopTimeUpdate.query.all()) >= 6
        db_trip_delayed = TripUpdate.find_by_dated_vj('trip:OCETrainTER-87212027-85000109-3:11859',
                                                      datetime.date(2015, 9, 21))
        assert db_trip_delayed

        assert db_trip_delayed.vj.navitia_trip_id == 'trip:OCETrainTER-87212027-85000109-3:11859'
        assert db_trip_delayed.vj.circulation_date == datetime.date(2015, 9, 21)
        assert db_trip_delayed.vj_id == db_trip_delayed.vj.id
        assert db_trip_delayed.status == 'update'
        # 6 stop times must have been created
        assert len(db_trip_delayed.stop_time_updates) == 6
        assert db_trip_delayed.real_time_updates[0].contributor == 'realtime.ire'


def check_db_ire_96231_trip_removal():
    with app.app_context():
        assert len(RealTimeUpdate.query.all()) >= 1
        assert len(TripUpdate.query.all()) >= 1
        assert len(StopTimeUpdate.query.all()) >= 0
        db_trip_removal = TripUpdate.find_by_dated_vj('trip:OCETrainTER-87212027-85000109-3:11859',
                                                      datetime.date(2015, 9, 21))
        assert db_trip_removal

        assert db_trip_removal.vj.navitia_trip_id == 'trip:OCETrainTER-87212027-85000109-3:11859'
        assert db_trip_removal.vj.circulation_date == datetime.date(2015, 9, 21)
        assert db_trip_removal.vj_id == db_trip_removal.vj.id
        assert db_trip_removal.status == 'delete'
        # full trip removal : no stop_time to precise
        assert len(db_trip_removal.stop_time_updates) == 0


def check_db_ire_6113_trip_removal():
    with app.app_context():
        assert len(RealTimeUpdate.query.all()) >= 1
        assert len(TripUpdate.query.all()) >= 1
        assert len(StopTimeUpdate.query.all()) >= 0
        db_trip_removal = TripUpdate.find_by_dated_vj('trip:OCETGV-87686006-87751008-2:25768',
                                                      datetime.date(2015, 10, 6))
        assert db_trip_removal

        assert db_trip_removal.vj.navitia_trip_id == 'trip:OCETGV-87686006-87751008-2:25768'
        assert db_trip_removal.vj.circulation_date == datetime.date(2015, 10, 6)
        assert db_trip_removal.vj_id == db_trip_removal.vj.id
        assert db_trip_removal.status == 'delete'
        print db_trip_removal.message
        assert db_trip_removal.message == u'Accident à un Passage à Niveau'
        # full trip removal : no stop_time to precise
        assert len(db_trip_removal.stop_time_updates) == 0


def check_db_ire_JOHN_trip_removal():
    with app.app_context():
        assert len(RealTimeUpdate.query.all()) >= 1
        assert len(TripUpdate.query.all()) >= 2
        assert len(StopTimeUpdate.query.all()) >= 0
        db_trip1_removal = TripUpdate.find_by_dated_vj('trip:OCETGV-87686006-87751008-2:25768',
                                                      datetime.date(2015, 9, 21))
        assert db_trip1_removal

        assert db_trip1_removal.vj.navitia_trip_id == 'trip:OCETGV-87686006-87751008-2:25768'
        assert db_trip1_removal.vj.circulation_date == datetime.date(2015, 9, 21)
        assert db_trip1_removal.vj_id == db_trip1_removal.vj.id
        assert db_trip1_removal.status == 'delete'
        # full trip removal : no stop_time to precise
        assert len(db_trip1_removal.stop_time_updates) == 0


        db_trip2_removal = TripUpdate.find_by_dated_vj('trip:OCETrainTER-87212027-85000109-3:11859',
                                                      datetime.date(2015, 9, 21))
        assert db_trip2_removal

        assert db_trip2_removal.vj.navitia_trip_id == 'trip:OCETrainTER-87212027-85000109-3:11859'
        assert db_trip2_removal.vj.circulation_date == datetime.date(2015, 9, 21)
        assert db_trip2_removal.vj_id == db_trip2_removal.vj.id
        assert db_trip2_removal.status == 'delete'
        # full trip removal : no stop_time to precise
        assert len(db_trip2_removal.stop_time_updates) == 0


def test_ire_delayed_simple_post(mock_rabbitmq):
    """
    simple delayed stops post
    """
    ire_96231 = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_ire_96231_delayed()
    assert mock_rabbitmq.call_count == 1


def test_ire_trip_removal_simple_post(mock_rabbitmq):
    """
    simple trip removal post
    """
    ire_6113 = get_ire_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_6113_trip_removal()
    assert mock_rabbitmq.call_count == 1


def test_ire_delayed_and_trip_removal_post(mock_rabbitmq):
    """
    post delayed stops on one trip than trip removal on another
    """
    ire_96231 = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    ire_6113 = get_ire_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_ire_96231_delayed()
    check_db_ire_6113_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_removal_post_twice(mock_rabbitmq):
    """
    double trip removal post
    """
    ire_6113 = get_ire_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_6113_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_delayed_post_twice(mock_rabbitmq):
    """
    double delayed stops post
    """
    ire_96231 = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_ire_96231_delayed()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_delayed_then_removal(mock_rabbitmq):
    """
    post delayed stops then trip removal on the same trip
    """
    ire_96231_delayed = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231_delayed)
    assert res == 'OK'
    ire_96231_trip_removal = get_ire_data('train_96231_trip_removal.xml')
    res = api_post('/ire', data=ire_96231_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_96231_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_two_trip_removal_one_post(mock_rabbitmq):
    """
    post one ire trip removal on two trips
    (navitia mock returns 2 vj for 'JOHN' headsign)
    """
    ire_JOHN_trip_removal = get_ire_data('train_JOHN_trip_removal.xml')
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_JOHN_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 1


def test_ire_two_trip_removal_post_twice(mock_rabbitmq):
    """
    post twice ire trip removal on two trips
    """
    ire_JOHN_trip_removal = get_ire_data('train_JOHN_trip_removal.xml')
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_JOHN_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_removal_parity(mock_rabbitmq):
    """
    simple parity trip removal post
    """
    ire_6113 = get_ire_data('train_6113_trip_removal.xml')
    ire_6113_14 = ire_6113.replace('<NumeroTrain>006113</NumeroTrain>',
                                   '<NumeroTrain>006113/14</NumeroTrain>')
    res = api_post('/ire', data=ire_6113_14)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_ire_6113_trip_removal()
    assert mock_rabbitmq.call_count == 1
