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
from kirin.core.handler import handle
from kirin.core.model import RealTimeUpdate, TripUpdate, VehicleJourney, StopTimeUpdate
import datetime
from kirin import app, db


def create_trip_update(id, trip_id, circulation_date, stops):
    trip_update = TripUpdate()
    trip_update.id = id
    vj = VehicleJourney({'id': trip_id}, circulation_date)
    trip_update.vj = vj
    for stop in stops:
        st = StopTimeUpdate({'id': stop['id']}, stop['departure'], stop['arrival'])
        st.arrival_status = stop['arrival_status']
        st.departure_status = stop['departure_status']
        trip_update.stop_time_updates.append(st)

    db.session.add(vj)
    db.session.add(trip_update)
    return trip_update

@pytest.fixture()
def setup_database():
    """
    we create two realtime_updates with the same vj but for different date
    and return a vj for navitia
    """
    with app.app_context():
        vju = create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d3', 'vehicle_journey:1', datetime.date(2015, 9, 8),
                [
                    {'id': 'sa:1', 'departure': datetime.datetime(2015, 9, 8, 8, 15), 'arrival': None, 'departure_status': 'update', 'arrival_status': 'none'},
                    {'id': 'sa:2', 'departure': datetime.datetime(2015, 9, 8, 9, 10), 'arrival': datetime.datetime(2015, 9, 8, 9, 5), 'departure_status': 'none', 'arrival_status': 'none'},
                    {'id': 'sa:3', 'departure': None, 'arrival': datetime.datetime(2015, 9, 8, 10, 5), 'departure_status': 'none', 'arrival_status': 'none'},
                    ])
        rtu = RealTimeUpdate(None, 'ire')
        rtu.id = '10866ce8-0638-4fa1-8556-1ddfa22d09d3'
        rtu.trip_updates.append(vju)
        db.session.add(rtu)
        vju = create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d4', 'vehicle_journey:1', datetime.date(2015, 9, 7),
                [
                    {'id': 'sa:1', 'departure': datetime.datetime(2015, 9, 7, 8, 35), 'arrival': None, 'departure_status': 'update', 'arrival_status': 'none'},
                    {'id': 'sa:2', 'departure': datetime.datetime(2015, 9, 7, 9, 40), 'arrival': datetime.datetime(2015, 9, 7, 9, 35), 'departure_status': 'update', 'arrival_status': 'update'},
                    {'id': 'sa:3', 'departure': None, 'arrival': datetime.datetime(2015, 9, 7, 10, 35), 'departure_status': 'none', 'arrival_status': 'update'},
                    ])
        rtu = RealTimeUpdate(None, 'ire')
        rtu.id = '20866ce8-0638-4fa1-8556-1ddfa22d09d3'
        rtu.trip_updates.append(vju)
        db.session.add(rtu)
        db.session.commit()

@pytest.fixture()
def navitia_vj():
    return {'id': 'vehicle_journey:1', 'stop_times': [
        {'arrival_time': None, 'departure_time': datetime.time(8, 10), 'stop_point': {'id': 'sa:1'}},
        {'arrival_time': datetime.time(9, 5), 'departure_time': datetime.time(9, 10), 'stop_point': {'id': 'sa:2'}},
        {'arrival_time': datetime.time(10, 5), 'departure_time': None, 'stop_point': {'id': 'sa:3'}}
        ]}



def test_handle_basic():
    with pytest.raises(TypeError):
        handle(None)

    #a RealTimeUpdate without any TripUpdate doesn't do anything
    real_time_update = RealTimeUpdate(raw_data=None, connector='test')
    res = handle(real_time_update)
    assert res == real_time_update


def test_handle_new_vj():
    """an easy one: we have one vj with only one stop time updated"""
    navitia_vj = {'id': 'vehicle_journey:1', 'stop_times': [
        {'arrival_time': None, 'departure_time': datetime.time(8, 10), 'stop_point': {'id': 'sa:1'}},
        {'arrival_time': datetime.time(9, 10), 'departure_time': None, 'stop_point': {'id': 'sa:2'}}
        ]}
    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        st = StopTimeUpdate({'id': 'sa:1'}, departure=datetime.datetime(2015, 9, 8, 8, 15), arrival=None)
        real_time_update = RealTimeUpdate(raw_data=None, connector='test')
        real_time_update.trip_updates.append(trip_update)
        trip_update.stop_time_updates.append(st)
        res = handle(real_time_update)

        assert len(res.trip_updates) == 1
        trip_update = res.trip_updates[0]
        assert len(trip_update.stop_time_updates) == 2
        assert trip_update.stop_time_updates[0].stop_id == 'sa:1'
        assert trip_update.stop_time_updates[0].departure == datetime.datetime(2015, 9, 8, 8, 15)
        assert trip_update.stop_time_updates[0].arrival == None

        assert trip_update.stop_time_updates[1].stop_id == 'sa:2'
        assert trip_update.stop_time_updates[1].departure == None
        assert trip_update.stop_time_updates[1].arrival == datetime.datetime(2015, 9, 8, 9, 10)


def test_handle_new_trip_out_of_order(navitia_vj):
    """
    We have one vj with only one stop time updated, but it's not the first
    so we have to reorder the stop times in the resulting trip_update
    """
    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        st = StopTimeUpdate({'id': 'sa:2'}, departure=datetime.datetime(2015, 9, 8, 9, 50), arrival=datetime.datetime(2015, 9, 8, 9, 49))
        real_time_update = RealTimeUpdate(raw_data=None, connector='test')
        real_time_update.trip_updates.append(trip_update)
        trip_update.stop_time_updates.append(st)
        res = handle(real_time_update)

        assert len(res.trip_updates) == 1
        trip_update = res.trip_updates[0]
        assert len(trip_update.stop_time_updates) == 3
        assert trip_update.stop_time_updates[0].stop_id == 'sa:1'
        assert trip_update.stop_time_updates[0].departure == datetime.datetime(2015, 9, 8, 8, 10)
        assert trip_update.stop_time_updates[0].arrival == None

        assert trip_update.stop_time_updates[1].stop_id == 'sa:2'
        assert trip_update.stop_time_updates[1].departure == datetime.datetime(2015, 9, 8, 9, 50)
        assert trip_update.stop_time_updates[1].arrival == datetime.datetime(2015, 9, 8, 9, 49)

        assert trip_update.stop_time_updates[2].stop_id == 'sa:3'
        assert trip_update.stop_time_updates[2].departure == None
        assert trip_update.stop_time_updates[2].arrival == datetime.datetime(2015, 9, 8, 10, 5)


def test_handle_update_vj(setup_database, navitia_vj):
    """
    this time we receive an update for a vj already in the database
    """
    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        st = StopTimeUpdate({'id': 'sa:2'}, departure=datetime.datetime(2015, 9, 8, 9, 20), arrival=datetime.datetime(2015, 9, 8, 9, 15))
        st.arrival_status = st.departure_status = 'update'
        real_time_update = RealTimeUpdate(raw_data=None, connector='test')
        real_time_update.id = '30866ce8-0638-4fa1-8556-1ddfa22d09d3'
        real_time_update.trip_updates.append(trip_update)
        trip_update.stop_time_updates.append(st)
        res = handle(real_time_update)

        assert len(real_time_update.trip_updates) == 1
        trip_update = real_time_update.trip_updates[0]
        assert len(trip_update.real_time_updates) == 2
        assert len(trip_update.stop_time_updates) == 3

        assert trip_update.stop_time_updates[0].stop_id == 'sa:1'
        assert trip_update.stop_time_updates[0].departure == datetime.datetime(2015, 9, 8, 8, 15)
        assert trip_update.stop_time_updates[0].arrival == None

        assert trip_update.stop_time_updates[1].stop_id == 'sa:2'
        assert trip_update.stop_time_updates[1].arrival == datetime.datetime(2015, 9, 8, 9, 15)
        assert trip_update.stop_time_updates[1].departure == datetime.datetime(2015, 9, 8, 9, 20)

        assert trip_update.stop_time_updates[2].stop_id == 'sa:3'
        assert trip_update.stop_time_updates[2].arrival == datetime.datetime(2015, 9, 8, 10, 5)
        assert trip_update.stop_time_updates[2].departure == None
