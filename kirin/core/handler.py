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
import kirin
from kirin import gtfs_realtime_pb2

from kirin.core.model import RealTimeUpdate, TripUpdate, StopTimeUpdate
import datetime

def handle(real_time_update):
    """
    receive a RealTimeUpdate with at least one TripUpdate filled with the data received
    by the connector. each TripUpdate is associated with the VehicleJourney returned by jormugandr
    """
    if not real_time_update or not hasattr(real_time_update, 'trip_updates'):
        raise TypeError()

    for trip_update in real_time_update.trip_updates:
        #find if there already a row in db
        old = TripUpdate.find_by_vj(trip_update.vj.navitia_id, trip_update.vj.circulation_date)
        #merge the theoric, the current realtime, and the new relatime
        merge(trip_update, old)

    feed = convert_to_gtfsrt(real_time_update)

    publish(feed, real_time_update)

    return real_time_update



def merge(trip_update, old_trip_update):
    if old_trip_update:
        old_trip_update.merge(trip_update)
        current = trip_update
        #we have to link the old vj_update with the new real_time_update
        rtu = trip_update.real_time_updates.pop()
        old_trip_update.real_time_updates.append(rtu)
    else:
        current = trip_update
        merge_realtime_theoric(current, trip_update.vj.navitia_vj)
    return current

def merge_realtime_theoric(trip_update, navitia_vj):
    for idx, navitia_stop in enumerate(navitia_vj.get('stop_times', [])):
        stop_id = navitia_stop.get('stop_point', {}).get('id')
        stop = trip_update.find_stop(stop_id)
        #TODO: order is important...
        if not stop:
            departure_time = navitia_stop.get('departure_time')
            arrival_time = navitia_stop.get('arrival_time')
            departure = arrival = None
            #TODO handle past midnigth
            if departure_time:
                departure = datetime.datetime.combine(trip_update.vj.circulation_date, departure_time)
            if arrival_time:
                arrival = datetime.datetime.combine(trip_update.vj.circulation_date, arrival_time)

            st = StopTimeUpdate(navitia_stop['stop_point'], departure, arrival)
            #we want to keep the order
            trip_update.stop_time_updates.insert(idx, st)


def convert_to_gtfsrt(real_time_update):
    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.incrementality = gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL
    feed.header.gtfs_realtime_version = '42'  # TODO

    return feed


def publish(feed, rt_update):
    """
    send RT feed to navitia
    """
    kirin.rabbitmq_handler.publish(feed.SerializeToString(), rt_update.contributor)
