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

from kirin import gtfs_realtime_pb2, kirin_pb2, chaos_pb2
import datetime


def date_to_str(date):
    if date:
        return date.strftime("%Y%m%d")
    return None


def to_posix_time(date_time):
    if date_time:
        return int((date_time - datetime.datetime(1970, 1, 1)).total_seconds())
    return 0


def convert_to_gtfsrt(real_time_updates):
    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.incrementality = gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL
    feed.header.gtfs_realtime_version = '1'
    feed.header.timestamp = to_posix_time(datetime.datetime.utcnow())

    for real_time_update in real_time_updates:
        for trip_update in real_time_update.trip_updates:
            contributor = None
            if real_time_update.contributor:
                contributor = real_time_update.contributor
            fill_entity(feed.entity.add(), trip_update, contributor)

    return feed


def fill_stop_times(pb_stop_time, stop_time):
    pb_stop_time.stop_id = stop_time.stop_id
    pb_stop_time.arrival.time = to_posix_time(stop_time.arrival)
    pb_stop_time.departure.time = to_posix_time(stop_time.departure)


def fill_channel(pb_channel):
    pb_channel.id = '1'
    for type in chaos_pb2._CHANNEL_TYPE.values:
        pb_channel.types.append(type.number)


def fill_message(pb_trip_update, message):
    pb_message = pb_trip_update.Extensions[kirin_pb2.message]
    pb_message.text = message
    fill_channel(pb_message.channel)


def fill_trip_update(pb_trip_update, trip_update, contributor=None):
    pb_trip = pb_trip_update.trip
    if contributor:
        pb_trip.Extensions[kirin_pb2.contributor] = contributor
    if trip_update.message:
        fill_message(pb_trip_update, trip_update.message)

    vj = trip_update.vj
    if vj:
        pb_trip.trip_id = vj.navitia_trip_id
        pb_trip.start_date = date_to_str(vj.circulation_date)
        # TODO fill the right schedule_relationship
        if trip_update.status == 'delete':
            pb_trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.CANCELED
        else:
            pb_trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.SCHEDULED

        for stop_time_update in trip_update.stop_time_updates:
            fill_stop_times(pb_trip_update.stop_time_update.add(), stop_time_update)


def fill_entity(pb_entity, trip_update, contributor=None):
    pb_entity.id = trip_update.vj_id
    fill_trip_update(pb_entity.trip_update, trip_update, contributor)
