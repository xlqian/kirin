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
from datetime import timedelta

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
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire', contributor='realtime.ire')
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

        assert pb_trip_update.HasExtension(kirin_pb2.trip_message) == False
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
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire', contributor='realtime.ire')
        real_time_update.trip_updates.append(trip_update)
        st = StopTimeUpdate({'id': 'sa:1'}, departure=_dt("8:15"), departure_delay=timedelta(minutes=5),
                            arrival=None)
        trip_update.stop_time_updates.append(st)

        st = StopTimeUpdate({'id': 'sa:2'},
                            departure=_dt("8:21"), departure_delay=timedelta(minutes=-40),
                            arrival=_dt("8:20"), arrival_delay=timedelta(minutes=-40),
                            message="bob's on the track")
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
        assert pb_trip_update.HasExtension(kirin_pb2.trip_message) is False
        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) is False
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.SCHEDULED

        assert len(pb_trip_update.stop_time_update) == 2

        pb_stop_time = pb_trip_update.stop_time_update[0]
        assert pb_stop_time.stop_id == 'sa:1'
        assert pb_stop_time.arrival.time == 0
        assert pb_stop_time.arrival.delay == 0
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:15"))
        assert pb_stop_time.departure.delay == 5*60
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == ""

        pb_stop_time = pb_trip_update.stop_time_update[1]
        assert pb_stop_time.stop_id == 'sa:2'
        assert pb_stop_time.arrival.time == to_posix_time(_dt("8:20"))
        assert pb_stop_time.arrival.delay == -40*60
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:21"))
        assert pb_stop_time.departure.delay == -40*60
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == "bob's on the track"


def test_populate_pb_with_deleted_stop_time():
    """
    test protobuf for partial delete

    nav vj
    sa:1 * ---- * sa:2 * ---- * sa:3 * ---- * sa:4

    we stop the vj from going to sa:3 and sa:4

    sa:1 * ---- * sa:2

    And we delay sa:1 of 5 minutes

    Note: in the message sent sa:2 departure will be removed as well
    as sa:3 departures/arrival and sa:4' arrival
    """
    #we add another impacted stop time to the Model
    from datetime import time
    navitia_vj = {'trip': {'id': 'vehicle_journey:1'}, 'stop_times': [
        {'arrival_time': None, 'departure_time': time(8, 11), 'stop_point': {'id': 'sa:1'}},
        {'arrival_time': time(9, 10), 'departure_time': time(9, 11), 'stop_point': {'id': 'sa:2'}},
        {'arrival_time': time(10, 10), 'departure_time': time(10, 11), 'stop_point': {'id': 'sa:3'}},
        {'arrival_time': time(11, 10), 'departure_time': None, 'stop_point': {'id': 'sa:4'}}
        ]}

    with app.app_context():
        trip_update = TripUpdate()
        vj = VehicleJourney(navitia_vj, datetime.date(2015, 9, 8))
        trip_update.vj = vj
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire', contributor='realtime.ire')
        real_time_update.trip_updates.append(trip_update)
        st = StopTimeUpdate({'id': 'sa:1'}, departure=_dt("8:15"), departure_delay=timedelta(minutes=5),
                            arrival=None)
        trip_update.stop_time_updates.append(st)

        st = StopTimeUpdate({'id': 'sa:2'},
                            arrival=_dt("9:10"),
                            departure=_dt("9:11"), dep_status='delete',  # we delete the departure
                            message="bob's on the track")
        real_time_update.trip_updates[0].stop_time_updates.append(st)

        st = StopTimeUpdate({'id': 'sa:3'},
                            # Note: we still send the departure/arrival for coherence
                            arrival=_dt("10:10"), dep_status='delete',  # we delete both departure and arrival
                            departure=_dt("10:11"), arr_status='delete',
                            message="bob's on the track")
        real_time_update.trip_updates[0].stop_time_updates.append(st)

        st = StopTimeUpdate({'id': 'sa:4'},
                            arrival=_dt("11:10"), arr_status='delete',  # we delete only the arrival
                            departure=_dt("11:11"),
                            message="bob's on the track")
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
        assert pb_trip_update.HasExtension(kirin_pb2.trip_message) is False
        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) is False
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.SCHEDULED

        assert len(pb_trip_update.stop_time_update) == 4

        pb_stop_time = pb_trip_update.stop_time_update[0]
        assert pb_stop_time.stop_id == 'sa:1'
        assert pb_stop_time.arrival.time == 0
        assert pb_stop_time.arrival.delay == 0
        assert pb_stop_time.departure.time == to_posix_time(_dt("8:15"))
        assert pb_stop_time.departure.delay == 5*60
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == ""

        pb_stop_time = pb_trip_update.stop_time_update[1]
        assert pb_stop_time.stop_id == 'sa:2'
        assert pb_stop_time.arrival.time == to_posix_time(_dt("9:10"))
        assert pb_stop_time.arrival.delay == 0
        # the arrival at the stop is still scheduled, but the departure is skipped
        assert pb_stop_time.arrival.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SCHEDULED
        assert pb_stop_time.departure.time == to_posix_time(_dt("9:11"))
        assert pb_stop_time.departure.delay == 0
        assert pb_stop_time.departure.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == "bob's on the track"

        pb_stop_time = pb_trip_update.stop_time_update[2]
        assert pb_stop_time.stop_id == 'sa:3'
        # both departure and arrival are SKIPPED
        assert pb_stop_time.arrival.time == to_posix_time(_dt("10:10"))
        assert pb_stop_time.arrival.delay == 0
        assert pb_stop_time.arrival.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
        assert pb_stop_time.departure.time == to_posix_time(_dt("10:11"))
        assert pb_stop_time.departure.delay == 0
        assert pb_stop_time.departure.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == "bob's on the track"

        pb_stop_time = pb_trip_update.stop_time_update[3]
        assert pb_stop_time.stop_id == 'sa:4'
        # only the arrival is skipped, the departure does not exists as it's the last stop
        assert pb_stop_time.arrival.time == to_posix_time(_dt("11:10"))
        assert pb_stop_time.arrival.delay == 0
        assert pb_stop_time.arrival.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
        assert pb_stop_time.departure.time == to_posix_time(_dt("11:11"))
        assert pb_stop_time.departure.delay == 0
        assert pb_stop_time.departure.Extensions[kirin_pb2.stop_time_event_relationship] == \
               gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SCHEDULED
        assert pb_stop_time.Extensions[kirin_pb2.stoptime_message] == "bob's on the track"


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
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire', contributor='realtime.ire')
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
        assert pb_trip_update.HasExtension(kirin_pb2.trip_message) == True
        assert pb_trip_update.Extensions[kirin_pb2.trip_message] == 'Message Test'
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
        real_time_update = RealTimeUpdate(raw_data=None, connector='ire', contributor='realtime.ire')
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
        assert pb_trip_update.HasExtension(kirin_pb2.trip_message) == True
        assert pb_trip_update.Extensions[kirin_pb2.trip_message] == 'Message Test'
        assert pb_trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED

        assert pb_trip_update.trip.HasExtension(kirin_pb2.contributor) == True
        assert pb_trip_update.trip.Extensions[kirin_pb2.contributor] == 'kisio-digital'

        assert len(feed_entity.entity[0].trip_update.stop_time_update) == 0
