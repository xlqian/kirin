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

def test_handle_basic():
    with pytest.raises(TypeError):
        handle(None)

    #a RealTimeUpdate without any TripUpdate doesn't do anything
    real_time_update = RealTimeUpdate(raw_data=None, connector='test')
    res = handle(real_time_update)
    assert res == real_time_update


def test_handle_new_trip():
    pass
    #an easy one: we have one vj with only one stop time updated
    # trip_update = TripUpdate()
    # vj = VehicleJourney('vehicle_journey:1', datetime.date(2015, 9, 8))
    # trip_update.vj = vj
    # st_update = StopTimeUpdate(datetime.datetime(2015, 9, 8, 15, 2), datetime.datetime(2015, 9, 8, 15, 0))
    # real_time_update = RealTimeUpdate(raw_data=None, connector='test')
    # real_time_update.trip_updates.append(trip_update)
    # res = handle(real_time_update)



