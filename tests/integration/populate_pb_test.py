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

from kirin.core.model import RealTimeUpdate, TripUpdate, VehicleJourney, StopTimeUpdate
from kirin.core.populate_pb import convert_to_gtfsrt, to_posix_time
import datetime
from kirin import app, db
from kirin import gtfs_realtime_pb2, kirin_pb2, chaos_pb2
from tests.check_utils import _dt


def test_populate_pb_with_one_stop_time():
    """
    an easy one: we have one vj with only one stop time updated
    fill protobuf from trip_update
    Verify protobuf
    """
    navitia_vj = {'trip': {'id': 'vehicle_journey:1'}, 'stop_times': [
        {'arrival_time': None, 'departure_time': datetime.time(8, 10), 'stop_point': {'id': 'sa:1'}},
        {'arrival_time': datetime.time(9, 10), 'departure_time': None, 'stop_point': {'id': 'sa:2'}}
        ]}

    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        st = StopTimeUpdate({'id': 'sa:1'}, departure=_dt("8:15"), arrival=None)
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire')
        real_time_update.trip_updates.append(trip_update)
        trip_update.stop_time_updates.append(st)

        db.session.add(real_time_update)
        db.session.commit()

        feed_entity = convert_to_gtfsrt(real_time_update.trip_updates)

        assert feed_entity.header.incrementality == gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL
        assert feed_entity.header.gtfs_realtime_version == '1'
        pb_trip_update = feed_entity.entity[0].trip_update
        assert pb_trip_update.trip.trip_id == 'vehicle_journey:1'
        assert pb_trip_update.trip.start_date == '20150908'
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.SCHEDULED
        pb_stop_time = feed_entity.entity[0].trip_update.stop_time_update[0]
        assert pb_stop_time.arrival.time == 0
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:15"))
        assert pb_stop_time.stop_id == 'sa:1'

        assert pb_trip_update.HasExtension(kirin_pb2.message) == False
        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) == False


def test_populate_pb_with_two_stop_time():
    """
    an easy one: we have one vj with only one stop time updated
    fill protobuf from trip_update
    Verify protobuf
    """

    #we add another impacted stop time to the Model
    navitia_vj = {'trip': {'id': 'vehicle_journey:1'}, 'stop_times': [
        {'arrival_time': None, 'departure_time': datetime.time(8, 10), 'stop_point': {'id': 'sa:1'}},
        {'arrival_time': datetime.time(9, 10), 'departure_time': None, 'stop_point': {'id': 'sa:2'}}
        ]}

    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        st = StopTimeUpdate({'id': 'sa:1'}, departure=_dt("8:15"), arrival=None)
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire')
        real_time_update.trip_updates.append(trip_update)
        trip_update.stop_time_updates.append(st)

        st = StopTimeUpdate({'id': 'sa:2'},
                            departure=_dt("8:21"),
                            arrival=_dt("8:20"))
        real_time_update.trip_updates[0].stop_time_updates.append(st)

        db.session.add(real_time_update)
        db.session.commit()

        feed_entity = convert_to_gtfsrt(real_time_update.trip_updates)

        assert feed_entity.header.incrementality == gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL
        assert feed_entity.header.gtfs_realtime_version, '1'
        assert len(feed_entity.entity) == 1
        pb_trip_update = feed_entity.entity[0].trip_update
        assert pb_trip_update.trip.trip_id == 'vehicle_journey:1'
        assert pb_trip_update.trip.start_date == '20150908'
        assert pb_trip_update.HasExtension(kirin_pb2.message) == False
        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) == False
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.SCHEDULED

        assert len(pb_trip_update.stop_time_update) == 2

        pb_stop_time = pb_trip_update.stop_time_update[0]
        assert pb_stop_time.stop_id == 'sa:1'
        assert pb_stop_time.arrival.time == 0
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:15"))

        pb_stop_time = pb_trip_update.stop_time_update[1]
        assert pb_stop_time.stop_id == 'sa:2'
        assert pb_stop_time.arrival.time == to_posix_time(_dt("8:20"))
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:21"))


def test_populate_pb_with_cancelation():
    """
    VJ cancelation
    """
    navitia_vj = {'trip': {'id': 'vehicle_journey:1'}}

    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        trip_update.status = 'delete'
        trip_update.message = 'Message Test'
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire')
        trip_update.contributor = 'kisio-digital'
        real_time_update.trip_updates.append(trip_update)

        db.session.add(real_time_update)
        db.session.commit()

        feed_entity = convert_to_gtfsrt(real_time_update.trip_updates)

        assert feed_entity.header.incrementality == gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL
        assert feed_entity.header.gtfs_realtime_version == '1'
        pb_trip_update = feed_entity.entity[0].trip_update
        assert pb_trip_update.trip.trip_id == 'vehicle_journey:1'
        assert pb_trip_update.trip.start_date == '20150908'
        assert pb_trip_update.HasExtension(kirin_pb2.message) == True
        assert pb_trip_update.Extensions[kirin_pb2.message].text == 'Message Test'
        assert chaos_pb2.Channel.web in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        assert chaos_pb2.Channel.sms in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        for type in chaos_pb2._CHANNEL_TYPE.values:
            assert type.number in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED

        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) == True
        assert pb_trip_update.trip.Extensions[kirin_pb2.contributor] == 'kisio-digital'

        assert len(feed_entity.entity[0].trip_update.stop_time_update) == 0


def test_populate_pb_with_full_dataset():
    """
    VJ cancelation
    """
    navitia_vj = {'trip': {'id': 'vehicle_journey:1'}}

    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        trip_update.status = 'delete'
        trip_update.message = 'Message Test'
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire')
        trip_update.contributor = 'kisio-digital'
        real_time_update.trip_updates.append(trip_update)

        db.session.add(real_time_update)
        db.session.commit()

        feed_entity = convert_to_gtfsrt(real_time_update.trip_updates, gtfs_realtime_pb2.FeedHeader.FULL_DATASET)

        assert feed_entity.header.incrementality == gtfs_realtime_pb2.FeedHeader.FULL_DATASET
        assert feed_entity.header.gtfs_realtime_version == '1'
        pb_trip_update = feed_entity.entity[0].trip_update
        assert pb_trip_update.trip.trip_id == 'vehicle_journey:1'
        assert pb_trip_update.trip.start_date == '20150908'
        assert pb_trip_update.HasExtension(kirin_pb2.message) == True
        assert pb_trip_update.Extensions[kirin_pb2.message].text == 'Message Test'
        assert chaos_pb2.Channel.web in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        assert chaos_pb2.Channel.sms in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        for type in chaos_pb2._CHANNEL_TYPE.values:
            assert type.number in pb_trip_update.Extensions[kirin_pb2.message].channel.types
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED

        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) == True
        assert pb_trip_update.trip.Extensions[kirin_pb2.contributor] == 'kisio-digital'

        assert len(feed_entity.entity[0].trip_update.stop_time_update) == 0
