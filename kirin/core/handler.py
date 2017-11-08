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
from kirin.utils import get_timezone


def persist(real_time_update):
    """
    receive a RealTimeUpdate and persist it in the database
    """
    model.db.session.add(real_time_update)
    model.db.session.commit()


def log_stu_modif(trip_update, stu, string_additional_info):
    logger = logging.getLogger(__name__)
    logger.debug("TripUpdate {vj_id} on {date}, StopTimeUpdate {order} modified: {add_info}".format(
                    vj_id=trip_update.vj_id, date=trip_update.vj.get_utc_circulation_date(), order=stu.order,
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
            logger.warning("TripUpdate {vj_id} (navitia id: {nav_id}) on {date} rejected: "
                           "order problem [STU index ({stu_index}) != kirin index ({kirin_index})]".format(
                vj_id=trip_update.vj_id, nav_id=trip_update.vj.navitia_trip_id,
                date=trip_update.vj.get_utc_circulation_date(), stu_index=stu.order, kirin_index=current_order))
            return False

        # modifications
        if stu.arrival is None:
            stu.arrival = stu.departure
            if stu.arrival is None and previous_stu is not None:
                stu.arrival = previous_stu.departure
            if stu.arrival is None:
                logger.warning("TripUpdate {vj_id} (navitia id: {nav_id}) on {date} rejected: "
                               "StopTimeUpdate missing arrival time".format(
                    vj_id=trip_update.vj_id, nav_id=trip_update.vj.navitia_trip_id,
                    date=trip_update.vj.get_utc_circulation_date()))
                return False
            log_stu_modif(trip_update, stu, "arrival = {v}".format(v=stu.arrival))
            if not stu.arrival_delay and stu.departure_delay:
                stu.arrival_delay = stu.departure_delay
                log_stu_modif(trip_update, stu, "arrival_delay = {v}".format(v=stu.arrival_delay))

        if stu.departure is None:
            stu.departure = stu.arrival
            log_stu_modif(trip_update, stu, "departure = {v}".format(v=stu.departure))
            if not stu.departure_delay and stu.arrival_delay:
                stu.departure_delay = stu.arrival_delay
                log_stu_modif(trip_update, stu, "departure_delay = {v}".format(v=stu.departure_delay))

        if stu.arrival_delay is None:
            stu.arrival_delay = datetime.timedelta(0)
            log_stu_modif(trip_update, stu, "arrival_delay = {v}".format(v=stu.arrival_delay))

        if stu.departure_delay is None:
            stu.departure_delay = datetime.timedelta(0)
            log_stu_modif(trip_update, stu, "departure_delay = {v}".format(v=stu.departure_delay))

        if previous_stu is not None and previous_stu.departure > stu.arrival:
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
    Returns real_time_update and the log_dict
    """
    if not real_time_update:
        raise TypeError()

    id_timestamp_tuples = [(tu.vj.navitia_trip_id, tu.vj.get_start_timestamp()) for tu in trip_updates]
    old_trip_updates = TripUpdate.find_by_dated_vjs(id_timestamp_tuples)
    for trip_update in trip_updates:
        # find if there is already a row in db
        old = next((tu for tu in old_trip_updates if tu.vj.navitia_trip_id == trip_update.vj.navitia_trip_id
                    and tu.vj.get_start_timestamp() == trip_update.vj.get_start_timestamp()), None)
        # merge the base schedule, the current realtime, and the new realtime
        current_trip_update = merge(trip_update.vj.navitia_vj, old, trip_update)

        # manage and adjust consistency if possible
        if current_trip_update and manage_consistency(current_trip_update):
            # we have to link the current_vj_update with the new real_time_update
            # this link is done quite late to avoid too soon persistence of trip_update by sqlalchemy
            current_trip_update.real_time_updates.append(real_time_update)

    persist(real_time_update)

    feed = convert_to_gtfsrt(real_time_update.trip_updates)
    feed_str = feed.SerializeToString()
    publish(feed_str, contributor)

    data_time = datetime.datetime.utcfromtimestamp(feed.header.timestamp)
    log_dict = {'contributor': contributor, 'timestamp': data_time, 'trip_update_count': len(feed.entity),
                'size': len(feed_str)}
    return real_time_update, log_dict


def _get_datetime(local_circulation_date, time, timezone):
    dt = datetime.datetime.combine(local_circulation_date, time)
    dt = timezone.localize(dt).astimezone(pytz.UTC)
    # in the db dt with timezone cannot coexist with dt without tz
    # since at the beginning there was dt without tz, we need to erase the tz info
    return dt.replace(tzinfo=None)


def _get_dep_update_info_of_stop_time(base_departure, new_st):
    dep = status = delay = None
    if new_st.departure_status == 'update':
        dep = (base_departure + new_st.departure_delay) if base_departure else None
        status = new_st.departure_status
        delay = new_st.departure_delay
    elif new_st.departure_status == 'delete':
        # passing status delete on the stoptime
        # Note: we keep providing base_schedule stoptime to better identify the stoptime
        # in the vj (for lolipop lines for example)
        status = new_st.departure_status
    else:
        dep = base_departure
    return dep, status, delay or timedelta(0)


def _get_arr_update_info_of_stop_time(base_arrival, new_st):
    arr = status = delay = None
    if new_st.arrival_status == 'update':
        arr = (base_arrival + new_st.arrival_delay) if base_arrival else None
        delay = new_st.arrival_delay
        status = new_st.arrival_status
    elif new_st.arrival_status == 'delete':
        status = new_st.arrival_status
    else:
        arr = base_arrival
    return arr, status, delay or timedelta(0)


def _get_updated_info(base_arrival, base_departure, last_departure, new_st):
    dep, dep_status, dep_delay = _get_dep_update_info_of_stop_time(base_departure, new_st)
    arr, arr_status, arr_delay = _get_arr_update_info_of_stop_time(base_arrival, new_st)

    # in case where arrival/departure time are None
    arr = arr or dep or last_departure
    dep = dep or arr

    # in case where arrival/departure time are None
    if last_departure and last_departure > arr:
        arr_delay += (last_departure - arr)
        arr = last_departure

    # in the real world, the departure time must be greater or equal to the arrival time
    if arr > dep:
        dep_delay += (arr - dep)
        dep = arr

    return dep, dep_status, dep_delay, arr, arr_status, arr_delay


def merge(navitia_vj, db_trip_update, new_trip_update):
    """
    We need to merge the info from 3 sources:
        * the navitia base schedule
        * the trip update already in the db (potentially nonexistent)
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
    last_departure = None
    local_circulation_date = new_trip_update.vj.get_local_circulation_date()

    has_no_changes = True
    for current_order, navitia_stop in enumerate(navitia_vj.get('stop_times', [])):
        # TODO handle forbidden pickup/dropoff (in those case set departure/arrival at None)
        nav_departure_time = navitia_stop.get('departure_time')
        nav_arrival_time = navitia_stop.get('arrival_time')
        timezone = get_timezone(navitia_stop)

        # we compute the arrival time and departure time on base schedule and take past mid-night into
        # consideration
        base_arrival = base_departure = None
        if nav_arrival_time is not None:
            if last_nav_dep is not None and last_nav_dep > nav_arrival_time:
                # last departure is after arrival, it's a past-midnight
                local_circulation_date += timedelta(days=1)
            base_arrival = _get_datetime(local_circulation_date, nav_arrival_time, timezone)

        if nav_departure_time is not None:
            if nav_arrival_time is not None and nav_arrival_time > nav_departure_time:
                # departure is before arrival, it's a past-midnight
                local_circulation_date += timedelta(days=1)
            base_departure = _get_datetime(local_circulation_date, nav_departure_time, timezone)

        stop_id = navitia_stop.get('stop_point', {}).get('id')
        new_st = new_trip_update.find_stop(stop_id, current_order)

        if db_trip_update and new_st:
            """
            First case: we already have recorded the delay and we find update info in the new trip update
            Then      : we should probably update it
            """
            db_st = db_trip_update.find_stop(stop_id, len(res_stoptime_updates))
            res_st = db_st or StopTimeUpdate(navitia_stop['stop_point'])
            dep, dep_status, dep_delay, arr, arr_status, arr_delay = _get_updated_info(base_arrival,
                                                                                       base_departure,
                                                                                       last_departure,
                                                                                       new_st)
            has_no_changes &= False if not db_st else (db_st.departure == dep and
                                                       db_st.departure_delay == (dep_delay or timedelta(0)) and
                                                       db_st.departure_status == (dep_status or 'none') and
                                                       db_st.arrival == arr and
                                                       db_st.arrival_delay == (arr_delay or timedelta(0)) and
                                                       db_st.arrival_status == (arr_status or 'none') and
                                                       db_st.message == new_st.message)
            if not has_no_changes:
                res_st.message = new_st.message
                res_st.update_departure(time=dep, status=dep_status, delay=dep_delay)
                res_st.update_arrival(time=arr, status=arr_status, delay=arr_delay)
            last_departure = dep

        elif db_trip_update is None and new_st is not None:
            """
            Second case: we have not yet recorded the delay
            Then       : it's time to create one in the db
            """
            has_no_changes = False
            res_st = StopTimeUpdate(navitia_stop['stop_point'])
            dep, dep_status, dep_delay, arr, arr_status, arr_delay = _get_updated_info(base_arrival,
                                                                                       base_departure,
                                                                                       last_departure,
                                                                                       new_st)
            res_st.update_departure(time=dep, status=dep_status, delay=dep_delay)
            res_st.update_arrival(time=arr, status=arr_status, delay=arr_delay)
            res_st.message = new_st.message
            last_departure = dep
        elif db_trip_update is not None and new_st is None:
            """
            Third case: we have already recorded a delay but nothing is mentioned in the new trip update
            Then      : we do nothing but only update stop time's order(?)
            """
            # nothing in db and in new trip update, we take the base schedule
            db_st = db_trip_update.find_stop(stop_id, len(res_stoptime_updates))
            res_st = db_st or StopTimeUpdate(navitia_stop['stop_point'],
                                             departure=base_departure,
                                             arrival=base_arrival)
            has_no_changes &= False if not db_st else (db_st.order == current_order)
            last_departure = res_st.departure

        else:
            """
            Last case: nothing is recorded yet and there is no update info in the new trip update
            Then     : take the base schedule's arrival/departure time and let's create a whole new world!
            """
            has_no_changes = False
            res_st = StopTimeUpdate(navitia_stop['stop_point'], departure=base_departure, arrival=base_arrival)
            last_departure = base_departure

        res_st.order = current_order
        res_stoptime_updates.append(res_st)
        last_nav_dep = nav_departure_time

    if has_no_changes:
        return None

    res.stop_time_updates = res_stoptime_updates
    return res


def publish(feed, contributor):
    """
    send RT feed to navitia
    """
    try:
        kirin.rabbitmq_handler.publish(feed, contributor)

    except socket.error:
        logging.getLogger(__name__).exception('impossible to publish in rabbitmq')
        raise MessageNotPublished()
