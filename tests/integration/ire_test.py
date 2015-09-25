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


def test_ire_post(mock_rabbitmq):
    """
    simple xml post on the api
    """
    ire_96231 = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    ire_6113 = get_ire_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        # assert len(StopTimeUpdate.query.all()) == 5  # TODO should be 6, but is 10 for the moment
        # db_trip_updates = TripUpdate.query.join(VehicleJourney).order_by('circulation_date').all()
        #
        # assert len(db_trip_updates) == 2
        # db_trip_delayed = db_trip_updates[0]
        # assert db_trip_delayed.vj.navitia_id == 'vehicle_journey:OCETrainTER-87212027-85000109-3:11859'
        # assert db_trip_delayed.vj_id == db_trip_delayed.vj.id
        # assert db_trip_delayed.vj.circulation_date == datetime.date(2015, 9, 21)
        # assert db_trip_delayed.status == 'update'
        # # 5 stop times must have been created
        # assert len(db_trip_delayed.stop_time_updates) == 5
        #
        # db_trip_removal = db_trip_updates[1]
        # assert db_trip_removal.vj.navitia_id == 'vehicle_journey:OCETGV-87686006-87751008-2:25768'
        # assert db_trip_removal.vj.circulation_date == datetime.date(2015, 10, 6)
        # assert db_trip_removal.vj_id == db_trip_removal.vj.id
        # assert db_trip_removal.status == 'delete'
        # # full trip removal : no stop_time to precise
        # assert len(db_trip_removal.stop_time_updates) == 0

    # the rabbit mq has to have been called only once
    assert mock_rabbitmq.call_count == 2


def test_ire_post_no_data():
    """
    when no data is given, we got a 400 error
    """
    tester = app.test_client()
    resp = tester.post('/ire')
    assert resp.status_code == 400


