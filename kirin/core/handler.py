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
import datetime
import logging
import socket
from datetime import timedelta
import pytz

import kirin
from kirin.core import model
from kirin.core.model import TripUpdate, StopTimeUpdate
from kirin.core.populate_pb import convert_to_gtfsrt
from kirin.exceptions import MessageNotPublished
from kirin.utils import get_timezone, record_call


def persist(real_time_update):
    """
    receive a RealTimeUpdate and persist it in the database
    """
    model.db.session.add(real_time_update)
    model.db.session.commit()


def log_stu_modif(trip_update, stu, string_additional_info):
    logger = logging.getLogger(__name__)
    logger.debug("TripUpdate {vj_id} on {date}, StopTimeUpdate {order} modified: {add_info}".format(
                    vj_id=trip_update.vj_id, date=trip_update.vj.circulation_date, order=stu.order,
                    add_info=string_additional_info))


def manage_consistency(trip_update):
    """
    receive a TripUpdate, then manage and adjust it's consistency
    returns False if trip update cannot be managed
    """
    logger = logging.getLogger(__name__)
    previous_stu = None
    for current_order, stu in enumerate(trip_update.stop_time_updates):
        # rejections
        if stu.order != current_order:
            logger.warning("TripUpdate {vj_id} on {date} rejected: order problem".format(
                vj_id=trip_update.vj_id, date=trip_update.vj.circulation_date))
            return False

        # modifications
        if not stu.arrival:
            stu.arrival = stu.departure
            log_stu_modif(trip_update, stu, "arrival = {v}".format(v=stu.arrival))
            if not stu.arrival_delay and stu.departure_delay:
                stu.arrival_delay = stu.departure_delay
                log_stu_modif(trip_update, stu, "arrival_delay = {v}".format(v=stu.arrival_delay))

        if not stu.departure:
            stu.departure = stu.arrival
            log_stu_modif(trip_update, stu, "departure = {v}".format(v=stu.departure))
            if not stu.departure_delay and stu.arrival_delay:
                stu.departure_delay = stu.arrival_delay
                log_stu_modif(trip_update, stu, "departure_delay = {v}".format(v=stu.departure_delay))

        if not stu.arrival_delay:
            stu.arrival_delay = datetime.timedelta(0)
            log_stu_modif(trip_update, stu, "arrival_delay = {v}".format(v=stu.arrival_delay))

        if not stu.departure_delay:
            stu.departure_delay = datetime.timedelta(0)
            log_stu_modif(trip_update, stu, "departure_delay = {v}".format(v=stu.departure_delay))

        if previous_stu and previous_stu.departure > stu.arrival:
            delay_diff = previous_stu.departure_delay - stu.arrival_delay
            stu.arrival += delay_diff
            stu.arrival_delay += delay_diff
            log_stu_modif(trip_update, stu, "arrival = {a} and arrival_delay = {a_d}".format(
                                                        a=stu.arrival, a_d=stu.arrival_delay))

        if stu.arrival > stu.departure:
            stu.departure_delay += stu.arrival - stu.departure
            stu.departure = stu.arrival
            log_stu_modif(trip_update, stu, "departure = {a} and departure_delay = {a_d}".format(
                                                        a=stu.departure, a_d=stu.departure_delay))

        previous_stu = stu

    return True


def handle(real_time_update, trip_updates, contributor):
    """
    receive a RealTimeUpdate with at least one TripUpdate filled with the data received
    by the connector. each TripUpdate is associated with the VehicleJourney returned by jormugandr
    """
    if not real_time_update:
        raise TypeError()

    for trip_update in trip_updates:
        # find if there already a row in db
        old = TripUpdate.find_by_dated_vj(trip_update.vj.navitia_trip_id, trip_update.vj.circulation_date)
        # merge the theoric, the current realtime, and the new realtime
        current_trip_update = merge(trip_update.vj.navitia_vj, old, trip_update)

        # manage and adjust consistency if possible
        if manage_consistency(current_trip_update):
            # we have to link the current_vj_update with the new real_time_update
            # this link is done quite late to avoid too soon persistence of trip_update by sqlalchemy
            current_trip_update.real_time_updates.append(real_time_update)

    persist(real_time_update)

    feed = convert_to_gtfsrt(real_time_update.trip_updates)
    feed_len = publish(feed, contributor)
    data_time = datetime.datetime.utcfromtimestamp(feed.header.timestamp)
    log_dict = {'contributor': contributor, 'timestamp': data_time, 'trip_update_count': len(feed.entity),
                'size': feed_len}
    return real_time_update, log_dict


def _get_datetime(circulation_date, time, timezone):
    dt = datetime.datetime.combine(circulation_date, time)
    dt = timezone.localize(dt).astimezone(pytz.UTC)
    # in the db dt with timezone cannot coexist with dt without tz
    # since at the beginning there was dt without tz, we need to erase the tz info
    return dt.replace(tzinfo=None)


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
            - else if there is the stoptime in the db:
                we keep this db stoptime
            - else we keep the navitia's base schedule

    Note that the results is either 'db_trip_update' or 'new_trip_update'. Side effects on this object are
    thus wanted because of database persistency (update or creation of new objects)


    ** Important Note **:
    we DO NOT HANDLE changes in navitia's schedule for the moment
    it will need to be handled, but it will be done after
    """
    res = db_trip_update if db_trip_update else new_trip_update
    res_stoptime_updates = []

    res.status = new_trip_update.status
    if new_trip_update.message:
        res.message = new_trip_update.message
    res.contributor = new_trip_update.contributor

    if res.status == 'delete':
        # for trip cancellation, we delete all stoptimes update
        res.stop_time_updates = []
        return res

    last_nav_dep = None
    circulation_date = new_trip_update.vj.circulation_date
    for navitia_stop in navitia_vj.get('stop_times', []):
        stop_id = navitia_stop.get('stop_point', {}).get('id')
        new_st = new_trip_update.find_stop(stop_id)
        db_st = db_trip_update.find_stop(stop_id) if db_trip_update else None

        # TODO handle forbidden pickup/dropoff (in those case set departure/arrival at None)
        nav_departure_time = navitia_stop.get('departure_time')
        nav_arrival_time = navitia_stop.get('arrival_time')
        timezone = get_timezone(navitia_stop)

        arrival = departure = None
        if nav_arrival_time:
            if last_nav_dep and last_nav_dep > nav_arrival_time:
                # last departure is after arrival, it's a past-midnight
                circulation_date += timedelta(days=1)
            arrival = _get_datetime(circulation_date, nav_arrival_time, timezone)
        if nav_departure_time:
            if nav_arrival_time and nav_arrival_time > nav_departure_time:
                # departure is before arrival, it's a past-midnight
                circulation_date += timedelta(days=1)
            departure = _get_datetime(circulation_date, nav_departure_time, timezone)

        if new_st:
            res_st = db_st or StopTimeUpdate(navitia_stop['stop_point'])
            # we have an update on the stop time, we consider it
            if new_st.departure_status == 'update':
                dep = departure + new_st.departure_delay if departure else None
                res_st.update_departure(time=dep, status='update', delay=new_st.departure_delay)
            elif db_st:
                # we have no update on the departure for this st, we take it from the db (if it exists)
                res_st.update_departure(time=db_st.departure,
                                        status=db_st.departure_status,
                                        delay=db_st.departure_delay)
            else:
                # we store the base's schedule
                res_st.update_departure(time=departure, status='none', delay=None)
            if new_st.departure_status == 'delete':
                # passing status delete on the stoptime
                # Note: we keep providing base_schedule stoptime to better identify the stoptime
                # in the vj (for lolipop lines for example)
                res_st.update_departure(status='delete')

            if new_st.arrival_status == 'update':
                arr = arrival + new_st.arrival_delay if arrival else None
                res_st.update_arrival(time=arr, status='update', delay=new_st.arrival_delay)
            elif db_st:
                res_st.update_arrival(time=db_st.arrival,
                                      status=db_st.arrival_status,
                                      delay=db_st.arrival_delay)
            else:
                # we store the base's schedule
                res_st.update_arrival(time=arrival, status='none', delay=None)

            if new_st.arrival_status == 'delete':
                res_st.update_arrival(status='delete')

            res_st.message = new_st.message
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

        last_nav_dep = nav_departure_time

    res.stop_time_updates = res_stoptime_updates

    return res


def publish(feed, contributor):
    """
    send RT feed to navitia
    """
    try:
        feed_str = feed.SerializeToString()
        kirin.rabbitmq_handler.publish(feed_str, contributor)
        return len(feed_str)

    except socket.error:
        logging.getLogger(__name__).exception('impossible to publish in rabbitmq')
        raise MessageNotPublished()
