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

from kirin.core import model
from kirin.core.model import RealTimeUpdate, TripUpdate, StopTimeUpdate
import datetime
from kirin.core.populate_pb import convert_to_gtfsrt


def persist(real_time_update):
    """
    receive a RealTimeUpdate and persist it in the database
    """
    model.db.session.add(real_time_update)
    model.db.session.commit()


def handle(real_time_update, trip_updates, contributor):
    """
    receive a RealTimeUpdate with at least one TripUpdate filled with the data received
    by the connector. each TripUpdate is associated with the VehicleJourney returned by jormugandr
    """
    if not real_time_update:
        raise TypeError()

    for trip_update in trip_updates:
        #find if there already a row in db
        old = TripUpdate.find_by_dated_vj(trip_update.vj.navitia_trip_id, trip_update.vj.circulation_date)
        #merge the theoric, the current realtime, and the new relatime
        current_trip_update = merge(trip_update, old)

        # we have to link the current_vj_update with the new real_time_update
        # this link is done quite late to avoid too soon persistence of trip_update by sqlalchemy
        current_trip_update.real_time_updates.append(real_time_update)

    persist(real_time_update)

    feed = convert_to_gtfsrt(real_time_update.trip_updates)

    publish(feed, contributor)

    return real_time_update


def merge(trip_update, old_trip_update):
    """
    TODO: this will not work when navitia base schedule change
    it will need to be handled, but it will be done after
    """
    if old_trip_update:
        old_trip_update.merge(trip_update)
        current = old_trip_update
    else:
        current = trip_update
        merge_realtime_theoric(current, trip_update.vj.navitia_vj)
    if current.status == 'delete':
        current.stop_time_updates = []
    return current


def merge_realtime_theoric(trip_update, navitia_vj):
    for idx, navitia_stop in enumerate(navitia_vj.get('stop_times', [])):
        stop_id = navitia_stop.get('stop_point', {}).get('id')
        st = trip_update.find_stop(stop_id)
        #TODO: order is important...
        departure_time = navitia_stop.get('departure_time')
        arrival_time = navitia_stop.get('arrival_time')
        departure = arrival = None
        #TODO handle past midnight
        if departure_time:
            departure = datetime.datetime.combine(trip_update.vj.circulation_date, departure_time)
        if arrival_time:
            arrival = datetime.datetime.combine(trip_update.vj.circulation_date, arrival_time)

        if not st:
            st = StopTimeUpdate(navitia_stop['stop_point'], departure=departure, arrival=arrival)
            #we want to keep the order
            trip_update.stop_time_updates.insert(idx, st)
        else:
            if st.departure_status == 'update' and departure:
                st.departure = departure + st.departure_delay
            if st.arrival_status == 'update' and arrival:
                st.arrival = arrival + st.arrival_delay


def publish(feed, contributor):
    """
    send RT feed to navitia
    """
    kirin.rabbitmq_handler.publish(feed.SerializeToString(), contributor)
