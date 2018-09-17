# coding: utf8

# Copyright (c) 2001-2015, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
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

from kirin import app
from tests import mock_navitia
from tests.check_utils import get_fixture_data, api_post
from kirin.core.model import RealTimeUpdate, TripUpdate, StopTimeUpdate
from tests.integration.utils_sncf_test import check_db_96231_delayed, check_db_JOHN_trip_removal, \
    check_db_96231_trip_removal, check_db_6113_trip_removal, check_db_6114_trip_removal, check_db_96231_normal, \
    check_db_840427_partial_removal


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


def test_ire_delayed_simple_post(mock_rabbitmq):
    """
    simple delayed stops post
    """
    ire_96231 = get_fixture_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_96231_delayed(contributor='realtime.ire')
    assert mock_rabbitmq.call_count == 1


def test_ire_trip_removal_simple_post(mock_rabbitmq):
    """
    simple trip removal post
    """
    ire_6113 = get_fixture_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_6113_trip_removal()
    assert mock_rabbitmq.call_count == 1


def test_ire_delayed_and_trip_removal_post(mock_rabbitmq):
    """
    post delayed stops on one trip than trip removal on another
    """
    ire_96231 = get_fixture_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    ire_6113 = get_fixture_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_96231_delayed(contributor='realtime.ire')
    check_db_6113_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_removal_post_twice(mock_rabbitmq):
    """
    double trip removal post
    """
    ire_6113 = get_fixture_data('train_6113_trip_removal.xml')
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'
    res = api_post('/ire', data=ire_6113)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_6113_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_delayed_post_twice(mock_rabbitmq):
    """
    double delayed stops post
    """
    ire_96231 = get_fixture_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_96231_delayed(contributor='realtime.ire')
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_delayed_then_removal(mock_rabbitmq):
    """
    post delayed stops then trip removal on the same trip
    """
    ire_96231_delayed = get_fixture_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231_delayed)
    assert res == 'OK'
    ire_96231_trip_removal = get_fixture_data('train_96231_trip_removal.xml')
    res = api_post('/ire', data=ire_96231_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_96231_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_two_trip_removal_one_post(mock_rabbitmq):
    """
    post one ire trip removal on two trips
    (navitia mock returns 2 vj for 'JOHN' headsign)
    """
    ire_JOHN_trip_removal = get_fixture_data('train_JOHN_trip_removal.xml')
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_JOHN_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 1


def test_ire_two_trip_removal_post_twice(mock_rabbitmq):
    """
    post twice ire trip removal on two trips
    """
    ire_JOHN_trip_removal = get_fixture_data('train_JOHN_trip_removal.xml')
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'
    res = api_post('/ire', data=ire_JOHN_trip_removal)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 0
    check_db_JOHN_trip_removal()
    # the rabbit mq has to have been called twice
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_with_parity(mock_rabbitmq):
    """
    a trip with a parity has been impacted, there should be 2 VJ impacted
    """
    ire_6113 = get_fixture_data('train_6113_trip_removal.xml')
    ire_6113_14 = ire_6113.replace('<NumeroTrain>006113</NumeroTrain>',
                                   '<NumeroTrain>006113/4</NumeroTrain>')
    res = api_post('/ire', data=ire_6113_14)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1

        # there should be 2 trip updated,
        # - trip:OCETGV-87686006-87751008-2:25768-2 for the headsign 6114
        # - trip:OCETGV-87686006-87751008-2:25768 for the headsign 6113

        assert len(TripUpdate.query.all()) == 2
        assert len(StopTimeUpdate.query.all()) == 0

    check_db_6113_trip_removal()
    check_db_6114_trip_removal()

    assert mock_rabbitmq.call_count == 1


def test_ire_trip_with_parity_one_unknown_vj(mock_rabbitmq):
    """
    a trip with a parity has been impacted, but the train 6112 is not known by navitia
    there should be only the train 6113 impacted
    """
    ire_6113 = get_fixture_data('train_6113_trip_removal.xml')
    ire_6112_13 = ire_6113.replace('<NumeroTrain>006113</NumeroTrain>',
                                   '<NumeroTrain>006112/3</NumeroTrain>')
    res = api_post('/ire', data=ire_6112_13)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 0

    check_db_6113_trip_removal()

    assert mock_rabbitmq.call_count == 1


def test_save_bad_raw_ire():
    """
    send a bad formatted ire, the bad raw ire should be saved in db
    """
    bad_ire = get_fixture_data('bad_ire.xml')
    res = api_post('/ire', data=bad_ire, check=False)
    assert res[1] == 400
    assert res[0]['message'] == 'Invalid arguments'
    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert RealTimeUpdate.query.first().status == 'KO'
        assert RealTimeUpdate.query.first().error == \
            'invalid xml, impossible to find "Train" in xml elt InfoRetard'
        assert RealTimeUpdate.query.first().raw_data == bad_ire


def test_ire_delayed_then_OK(mock_rabbitmq):
    """
    We delay a stop, then the vj is back on time
    """
    ire_96231 = get_fixture_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
        assert RealTimeUpdate.query.first().status == 'OK'
    check_db_96231_delayed(contributor='realtime.ire')
    assert mock_rabbitmq.call_count == 1

    ire_96231 = get_fixture_data('train_96231_normal.xml')
    res = api_post('/ire', data=ire_96231)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 2
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
    check_db_96231_normal(contributor='realtime.ire')
    assert mock_rabbitmq.call_count == 2


def test_ire_trip_without_any_motifexterne(mock_rabbitmq):
    """
    a trip with a parity has been impacted, but the ExternModif is missing,
    the IRE should still be acceptable
    """
    ire_96231 = get_fixture_data('train_96231_delayed.xml')
    # Removing MotifExterne
    ire_96231_without_MotifExterne = ire_96231.replace('<MotifExterne>Affluence exceptionnelle de voyageurs</MotifExterne>',
                                                       '')
    res = api_post('/ire', data=ire_96231_without_MotifExterne)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 6
        assert RealTimeUpdate.query.first().status == 'OK'
    check_db_96231_delayed(contributor='realtime.ire', motif_externe_is_null=True)
    assert mock_rabbitmq.call_count == 1


def test_ire_partial_removal(mock_rabbitmq):
    """
    the trip 840427 has been partialy deleted

    Normally there are 7 stops in this VJ, but 4 (Chaumont, Bar-sur-Aube, Vendeuvre and Troyes) have been removed
    """
    ire_080427 = get_fixture_data('train_840427_partial_removal.xml')
    res = api_post('/ire', data=ire_080427)
    assert res == 'OK'

    with app.app_context():
        assert len(RealTimeUpdate.query.all()) == 1
        assert len(TripUpdate.query.all()) == 1
        assert len(StopTimeUpdate.query.all()) == 7
        assert RealTimeUpdate.query.first().status == 'OK'
    check_db_840427_partial_removal(contributor='realtime.ire')
    assert mock_rabbitmq.call_count == 1
