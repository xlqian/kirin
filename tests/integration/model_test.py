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

from kirin.core.model import VehicleJourney, TripUpdate, StopTimeUpdate
from kirin import db, app
import datetime
import pytest

def create_trip_update(id, trip_id, circulation_date):
    trip_update = TripUpdate()
    trip_update.id = id
    vj = VehicleJourney({'id':trip_id}, circulation_date)
    trip_update.vj = vj

    db.session.add(vj)
    db.session.add(trip_update)
    return trip_update

@pytest.fixture()
def setup_database():
    with app.app_context():
        create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d3', 'vehicle_journey:1', datetime.date(2015, 9, 8))
        create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d4', 'vehicle_journey:2', datetime.date(2015, 9, 8))
        create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d5', 'vehicle_journey:2', datetime.date(2015, 9, 9))
        db.session.commit()


def test_find_by_vj(setup_database):
    with app.app_context():
        assert TripUpdate.find_by_dated_vj('vehicle_journey:1', datetime.date(2015, 9, 9)) is None
        row = TripUpdate.find_by_dated_vj('vehicle_journey:1', datetime.date(2015, 9, 8))
        assert row is not None
        assert row.id == '70866ce8-0638-4fa1-8556-1ddfa22d09d3'

        row = TripUpdate.find_by_dated_vj('vehicle_journey:2', datetime.date(2015, 9, 8))
        assert row is not None
        assert row.id == '70866ce8-0638-4fa1-8556-1ddfa22d09d4'



def test_find_stop():
    with app.app_context():
        vj = create_trip_update('70866ce8-0638-4fa1-8556-1ddfa22d09d3', 'vj1', datetime.date(2015, 9, 8))
        st1 = StopTimeUpdate({'id': 'sa:1'}, None, None)
        vj.stop_time_updates.append(st1)
        st2 = StopTimeUpdate({'id': 'sa:2'}, None, None)
        vj.stop_time_updates.append(st2)
        st3 = StopTimeUpdate({'id': 'sa:3'}, None, None)
        vj.stop_time_updates.append(st3)

        assert vj.find_stop('sa:1') == st1
        assert vj.find_stop('sa:3') == st3
        assert vj.find_stop('sa:4') is None
