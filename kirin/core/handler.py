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
        current_trip_update = merge(trip_update.vj.navitia_vj, old, trip_update)

        # we have to link the current_vj_update with the new real_time_update
        # this link is done quite late to avoid too soon persistence of trip_update by sqlalchemy
        current_trip_update.real_time_updates.append(real_time_update)

    persist(real_time_update)

    feed = convert_to_gtfsrt(real_time_update.trip_updates)

    publish(feed, contributor)

    return real_time_update


def merge(navitia_vj, db_trip_update, new_trip_update):
    """
    We need to merge the info from 3 sources:
        * the navitia base schedule
        * the trip update already in the bd (potentially not existent)
        * the incoming trip update

    The result is either the db_trip_update if it exists, or the new_trip_update (it is updated as a side
    effect)

    The mechanism is quite simple:
        * the result trip status is the new_trip_update's status
            (ie in the db the trip was cancelled, and a new update is only an update, the trip update is
            not cancelled anymore, only updated)

        * for each navitia's stop_time and for departure|arrival:
            - if there is an update on this stoptime (in new_trip_update):
                we compute the new datetime based on the new information and the navitia's base schedule
            - else if there if the stoptime in the db:
                we keep this db stoptime
            - else we keep the navitia's base schedule

    ** Important Note **:
    we DO NOT HANDLE changes in navitia's schedule for the moment
    it will need to be handled, but it will be done after
    """
    res = db_trip_update if db_trip_update else new_trip_update
    res_stoptime_updates = []

    res.status = new_trip_update.status
    if new_trip_update.message:
        res.message = new_trip_update.message
    res.contributor = res.contributor

    if res.status == 'delete':
        # for trip cancellation, we delete all stoptimes update
        res.stop_time_updates = []
        return res

    for idx, navitia_stop in enumerate(navitia_vj.get('stop_times', [])):
        stop_id = navitia_stop.get('stop_point', {}).get('id')
        new_st = new_trip_update.find_stop(stop_id)
        db_st = db_trip_update.find_stop(stop_id) if db_trip_update else None
        #TODO: order is important...
        nav_departure_time = navitia_stop.get('departure_time')
        nav_arrival_time = navitia_stop.get('arrival_time')

        departure = arrival = None
        if nav_departure_time:
            departure = datetime.datetime.combine(new_trip_update.vj.circulation_date, nav_departure_time)
        if nav_arrival_time:
            arrival = datetime.datetime.combine(new_trip_update.vj.circulation_date, nav_arrival_time)

        #TODO handle past midnight

        if new_st:
            res_st = db_st or new_st
            # we have an update on the stop time, we consider it
            if new_st.departure_status == 'update':
                dep = departure + new_st.departure_delay if departure else None
                res_st.set_departure(dep, status='update', delay=new_st.departure_delay)
            elif db_st:
                # we have no update on the departure for this st, we take it from the db (if it exists)
                res_st.set_departure(db_st.departure,
                                     status=db_st.departure_status,
                                     delay=db_st.departure_delay)

            if new_st.arrival_status == 'update':
                arr = arrival + new_st.arrival_delay if arrival else None
                res_st.set_arrival(arr, status='update', delay=new_st.arrival_delay)
            elif db_st:
                res_st.set_arrival(db_st.arrival,
                                   status=db_st.arrival_status,
                                   delay=db_st.arrival_delay)

            # we might need to update the st's order
            res_st.order = len(res_stoptime_updates)
            res_stoptime_updates.append(res_st)
        elif db_st:
            db_st.order = len(res_stoptime_updates)
            res_stoptime_updates.append(db_st)
        else:
            # nothing in db and in new trip update, we take the base schedule
            new_st = StopTimeUpdate(navitia_stop['stop_point'], departure=departure, arrival=arrival)
            new_st.order = len(res_stoptime_updates)
            res_stoptime_updates.append(new_st)

    res.stop_time_updates = res_stoptime_updates

    return res


def publish(feed, contributor):
    """
    send RT feed to navitia
    """
    kirin.rabbitmq_handler.publish(feed.SerializeToString(), contributor)
