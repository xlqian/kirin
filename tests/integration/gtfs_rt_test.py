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
import pytest
from kirin.core.model import RealTimeUpdate, db
from kirin.gtfs_rt import gtfs_rt
from tests.check_utils import dumb_nav_wrapper
from kirin import gtfs_realtime_pb2, app

@pytest.fixture()
def basic_gtfs_rt_data():
    feed = gtfs_realtime_pb2.FeedMessage()

    entity = feed.entity.add()
    entity.trip.trip_id = "bob"

    stu = entity.stop_time_update.add()
    stu.arrival.delay = 60
    stu.stop_sequence = 1
    stu.stop_id = "first_stop"

    stu = entity.stop_time_update.add()
    stu.arrival.delay = 180
    stu.stop_sequence = 4
    stu.stop_id = "fourth_stop"

    return feed

def gtfs_model_builder_test(basic_gtfs_rt_data):
    with app.app_context():
        rt_update = RealTimeUpdate(basic_gtfs_rt_data, connector='gtfs-rt')
        trip_updates = gtfs_rt.KirinModelBuilder(dumb_nav_wrapper()).build(rt_update)

        # we associate the trip_update manually for sqlalchemy to make the links
        rt_update.trip_updates = trip_updates
        db.session.add(rt_update)
        db.session.commit()

        assert len(trip_updates) == 1
        # TODO!
