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
from kirin import app
from tests import mock_navitia
from tests.check_utils import get_ire_data


@pytest.fixture(scope='function', autouse=True)
def navitia(monkeypatch):
    """
    Mock all calls to navitia for this fixture
    """
    monkeypatch.setattr('navitia_wrapper._NavitiaWrapper.query', mock_navitia.mock_navitia_query)


def test_wrong_ire_post():
    """
    simple xml post on the api
    """
    res, status = api_post('/ire', check=False, data='<bob></bob>')

    assert status == 400

    print res.get('error') == 'invalid'


def test_ire_post():
    """
    simple xml post on the api
    """
    ire_96231 = get_ire_data('train_96231_delayed.xml')
    res = api_post('/ire', data=ire_96231)

    assert res == 'OK'


def test_ire_post_no_data():
    """
    when no data is given, we got a 400 error
    """
    tester = app.test_client()
    resp = tester.post('/ire')
    assert resp.status_code == 400


