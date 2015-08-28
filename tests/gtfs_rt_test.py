# -*- coding: utf-8 -*-

from kirin import gtfs_realtime_pb2
import calendar
from datetime import datetime
import pytz

def unix_time(y, m, d, h, min, s):
    while min >= 60:
        h += 1
        min -= 60
    tz = pytz.timezone("Europe/Paris")
    d = datetime(y, m, d, h, min, s, 0, tz)
    return calendar.timegm(d.utctimetuple())

def make_96231_20150728_0():
    """gtfs rt feed corresponding to Flux-96231_2015-07-28_0.xml"""

    message = gtfs_realtime_pb2.FeedMessage()

    message.header.incrementality = gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL

    entity = message.entity.add()
    entity.id = "96231_2015-07-28_0"
    trip_update = entity.trip_update

    trip = trip_update.trip
    trip.trip_id = "vehicle_journey:OCETrainTER-87212027-85000109-3:15554"
    trip.start_date = "20150728"
    trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.SCHEDULED

    # Strasbourg
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-87212027"
    stop_time.arrival.time = unix_time(2015, 07, 28, 17, 21, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 17, 21, 0)

    # Sélestat
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-87214056"
    stop_time.arrival.time = unix_time(2015, 07, 28, 17, 38, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 17, 40 + 15, 0)

    # Colmar
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-87182014"
    stop_time.arrival.time = unix_time(2015, 07, 28, 17, 51 + 15, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 17, 53 + 15, 0)

    # Mulhouse
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-87182063"
    stop_time.arrival.time = unix_time(2015, 07, 28, 18, 14 + 15, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 18, 16 + 15, 0)

    # St-Louis
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-87182139"
    stop_time.arrival.time = unix_time(2015, 07, 28, 18, 30 + 15, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 18, 31 + 15, 0)

    # Basel-SBB
    stop_time = trip_update.stop_time_update.add()
    stop_time.stop_id = "stop_point:OCE:SP:TrainTER-85000109"
    stop_time.arrival.time = unix_time(2015, 07, 28, 18, 39 + 15, 0)
    stop_time.departure.time = unix_time(2015, 07, 28, 18, 39, 0)# ?

    return message

if __name__ == "__main__":
    message = make_96231_20150728_0()
    print message
