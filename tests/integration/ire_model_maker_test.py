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

from kirin import db, app
from kirin.core import model
from kirin.ire.model_maker import KirinModelBuilder
import navitia_wrapper
from tests.check_utils import get_ire_data


def dumb_nav_wrapper():
    """return a dumb navitia wrapper (all the param are useless since the 'query' call has been mocked"""
    return navitia_wrapper.Navitia(url='').instance('')


def test_train_delayed(mock_navitia_fixture):
    """
    test the import of train_96231_delayed.xml
    """

    input_train_delayed = get_ire_data('train_96231_delayed.xml')

    with app.app_context():
        rt_update = model.RealTimeUpdate(input_train_delayed, connector='ire')
        KirinModelBuilder(dumb_nav_wrapper()).build(rt_update)
        db.session.add(rt_update)
        db.session.commit()

        assert len(rt_update.trip_updates) == 1
        trip_up = rt_update.trip_updates[0]
        assert trip_up.vj.navitia_id == 'vehicle_journey:OCETrainTER-87212027-85000109-3:11859'
        assert trip_up.vj_id == trip_up.vj.id

        # 5 stop times must have been created
        #assert len(trip_up.stop_time_updates) == 5

