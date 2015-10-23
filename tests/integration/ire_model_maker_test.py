# coding=utf-8
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
from datetime import timedelta
import pytest

from kirin import db, app
from kirin.core import model
from kirin.ire.model_maker import KirinModelBuilder
import navitia_wrapper
from tests.check_utils import get_ire_data, _dt


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
        trip_updates = KirinModelBuilder(dumb_nav_wrapper()).build(rt_update)

        # we associate the trip_update manually for sqlalchemy to make the links
        rt_update.trip_updates = trip_updates
        db.session.add(rt_update)
        db.session.commit()

        assert len(trip_updates) == 1
        trip_up = trip_updates[0]
        assert trip_up.vj.navitia_trip_id == 'trip:OCETrainTER-87212027-85000109-3:11859'
        assert trip_up.vj_id == trip_up.vj.id
        assert trip_up.status == 'update'

        # 5 stop times must have been created
        assert len(trip_up.stop_time_updates) == 5

        # first stop time should be 'gare de Sélestat'
        st = trip_up.stop_time_updates[0]
        assert st.id
        assert st.stop_id == 'stop_point:OCE:SP:TrainTER-87214056'
        # the arrival is not in the IRE data, so the status is 'none'
        assert st.arrival is None  # not computed yet
        assert st.arrival_delay is None
        assert st.arrival_status == 'none'
        assert st.departure is None
        assert st.departure_delay == timedelta(minutes=15)
        assert st.departure_status == 'update'

        # second should be 'gare de Colmar'
        st = trip_up.stop_time_updates[1]
        assert st.id
        assert st.stop_id == 'stop_point:OCE:SP:TrainTER-87182014'
        assert st.arrival is None
        assert st.arrival_delay == timedelta(minutes=15)
        assert st.arrival_status == 'update'
        assert st.departure is None
        assert st.departure_delay == timedelta(minutes=15)
        assert st.departure_status == 'update'

        # last should be 'gare de Basel-SBB'
        st = trip_up.stop_time_updates[-1]
        assert st.id
        assert st.stop_id == 'stop_point:OCE:SP:TrainTER-85000109'
        assert st.arrival is None
        assert st.arrival_delay == timedelta(minutes=15)
        assert st.arrival_status == 'update'
        # no departure in ire since it's the last (thus the departure will be before the arrival)
        assert st.departure is None
        assert st.departure_delay is None
        assert st.departure_status == 'none'


def test_train_trip_removal(mock_navitia_fixture):
    """
    test the import of train_6113_trip_removal.xml
    """

    input_train_trip_removed = get_ire_data('train_6113_trip_removal.xml')

    with app.app_context():
        rt_update = model.RealTimeUpdate(input_train_trip_removed, connector='ire')
        trip_updates = KirinModelBuilder(dumb_nav_wrapper()).build(rt_update)
        rt_update.trip_updates = trip_updates
        db.session.add(rt_update)
        db.session.commit()

        assert len(trip_updates) == 1
        trip_up = trip_updates[0]
        assert trip_up.vj.navitia_trip_id == 'trip:OCETGV-87686006-87751008-2:25768'
        assert trip_up.vj_id == trip_up.vj.id
        assert trip_up.status == 'delete'
        # full trip removal : no stop_time to precise
        assert len(trip_up.stop_time_updates) == 0
