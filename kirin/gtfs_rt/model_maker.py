# Copyright (c) 2001-2017, Canal TP and/or its affiliates. All rights reserved.
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
from kirin import gtfs_realtime_pb2
import logging
import pytz

from kirin import core
from kirin.core import model
from kirin.exceptions import KirinException, InvalidArguments, ObjectNotFound
from kirin.utils import make_navitia_wrapper, make_rt_update, floor_datetime
from kirin import new_relic
from kirin.utils import record_internal_failure, record_call
from kirin.utils import get_timezone


def handle(proto, navitia_wrapper, contributor):
    data = str(proto)  # temp, for the moment, we save the protobuf as text
    rt_update = make_rt_update(data, 'gtfs-rt', contributor=contributor)
    start_datetime = datetime.datetime.utcnow()
    try:
        trip_updates = KirinModelBuilder(navitia_wrapper, contributor).build(rt_update, data=proto)
        record_call('OK', contributor=contributor)
    except KirinException as e:
        rt_update.status = 'KO'
        rt_update.error = e.data['error']
        model.db.session.add(rt_update)
        model.db.session.commit()
        record_call('failure', reason=str(e), contributor=contributor)
        raise
    except Exception as e:
        rt_update.status = 'KO'
        rt_update.error = e.message
        model.db.session.add(rt_update)
        model.db.session.commit()
        record_call('failure', reason=str(e), contributor=contributor)
        raise

    _, log_dict = core.handle(rt_update, trip_updates, contributor)
    duration = (datetime.datetime.utcnow() - start_datetime).total_seconds()
    log_dict.update({'duration': duration,
                     'input_timestamp': datetime.datetime.utcfromtimestamp(proto.header.timestamp)})
    record_call('Simple feed publication', **log_dict)
    logging.getLogger(__name__).info('Simple feed publication', extra=log_dict)


def to_str(date):
    # the date is in UTC, thus we don't have to care about the coverage's timezone
    return date.strftime("%Y%m%dT%H%M%SZ")


class KirinModelBuilder(object):

    def __init__(self, nav, contributor=None):
        self.navitia = nav
        self.contributor = contributor
        self.log = logging.getLogger(__name__)
        # TODO better period handling
        self.period_filter_tolerance = datetime.timedelta(hours=3)
        self.stop_code_key = 'source'  # TODO conf

    def build(self, rt_update, data):
        """
        parse the protobuf in the rt_update object
        and return a list of trip updates

        The TripUpdates are not yet associated with the RealTimeUpdate
        """
        self.log.debug("proto = {}".format(data))
        data_time = datetime.datetime.utcfromtimestamp(data.header.timestamp)

        trip_updates = []
        for entity in data.entity:
            if not entity.trip_update:
                continue
            tu = self._make_trip_updates(entity.trip_update, data_time=data_time)
            trip_updates.extend(tu)
        return trip_updates

    def _make_trip_updates(self, input_trip_update, data_time):
        vjs = self._get_navitia_vjs(input_trip_update.trip, data_time=data_time)

        trip_updates = []
        for vj in vjs:
            trip_update = model.TripUpdate(vj=vj)
            trip_update.contributor = self.contributor
            trip_updates.append(trip_update)

            for input_st_update in input_trip_update.stop_time_update:
                st_update = self._make_stoptime_update(input_st_update, vj.navitia_vj)
                if st_update is None:
                    continue
                trip_update.stop_time_updates.append(st_update)

        return trip_updates

    def _get_navitia_vjs(self, trip, data_time):
        vj_source_code = trip.trip_id

        since = floor_datetime(data_time - self.period_filter_tolerance)
        until = floor_datetime(data_time + self.period_filter_tolerance + datetime.timedelta(hours=1))
        self.log.debug('searching for vj {} on [{}, {}] in navitia'.format(vj_source_code, since, until))

        navitia_vjs = self.navitia.vehicle_journeys(q={
            'filter': 'vehicle_journey.has_code({}, {})'.format(self.stop_code_key, vj_source_code),
            'since': to_str(since),
            'until': to_str(until),
            'depth': '2',  # we need this depth to get the stoptime's stop_area
        })

        if not navitia_vjs:
            self.log.info('impossible to find vj {t} on [{s}, {u}]'
                          .format(t=vj_source_code,
                                  s=since,
                                  u=until))
            record_internal_failure('missing vj', contributor=self.contributor)
            return []

        if len(navitia_vjs) > 1:
            vj_ids = [vj.get('id') for vj in navitia_vjs]
            self.log.info('too many vjs found for {t} on [{s}, {u}]: {ids}'
                          .format(t=vj_source_code,
                                  s=since,
                                  u=until,
                                  ids=vj_ids
                                  ))
            record_internal_failure('duplicate vjs', contributor=self.contributor)
            return []
       
        nav_vj = navitia_vjs[0]

        # Now we compute the real circulate_date of VJ from since, until and vj's first stop_time
        # We do this to prevent cases like pass midnight when [since, until] is too large
        # the final circulate_date in database is in local timezone
        first_stop_time = nav_vj.get('stop_times', [{}])[0]
        tzinfo = get_timezone(first_stop_time)

        # 'since' and 'until' must have a timezone before being converted to local timezone
        local_since = pytz.utc.localize(since).astimezone(tzinfo)
        local_until = pytz.utc.localize(until).astimezone(tzinfo)

        circulate_date = None

        if local_since.date() == local_until.date():
            circulate_date = local_since.date()
        else:
            arrival_time = first_stop_time['arrival_time']
            # At first, we suppose that the circulate_date is local_since's date
            if local_since < tzinfo.localize(datetime.datetime.combine(local_since.date(),
                                                                       arrival_time)) < local_until:
                circulate_date = local_since.date()
            elif local_since < tzinfo.localize(datetime.datetime.combine(local_until.date(),
                                                                         arrival_time)) < local_until:
                circulate_date = local_until.date()
            else:
                self.log.error('impossible to calculate the circulate date of vj: {}'.format(nav_vj.get('id')))
                record_internal_failure('impossible to calculate the circulate date of vj', contributor=self.contributor)

        if circulate_date is None:
            return []

        return [model.VehicleJourney(nav_vj, circulate_date)]


    def _make_stoptime_update(self, input_st_update, navitia_vj):
        nav_st = self._get_navitia_stop_time(input_st_update, navitia_vj)

        if nav_st is None:
            self.log.info('impossible to find stop point {} in the vj {}, skipping it'.format(
                input_st_update.stop_id, navitia_vj.get('id')))
            record_internal_failure('missing stop point', contributor=self.contributor)
            return None

        nav_stop = nav_st.get('stop_point', {})

        # TODO handle delay uncertainty
        # TODO handle schedule_relationship
        def read_delay(st_event):
            if st_event and st_event.delay:
                return datetime.timedelta(seconds=st_event.delay)
        dep_delay = read_delay(input_st_update.departure)
        arr_delay = read_delay(input_st_update.arrival)
        dep_status = 'none' if dep_delay is None else 'update'
        arr_status = 'none' if arr_delay is None else 'update'


        st_update = model.StopTimeUpdate(nav_stop, departure_delay=dep_delay, arrival_delay=arr_delay,
                                         dep_status=dep_status, arr_status=arr_status)

        return st_update

    def _get_navitia_stop_time(self, input_st_update, navitia_vj):
        # TODO use input_st_update.stop_sequence to get the right stop_time even for loops
        for s in navitia_vj.get('stop_times', []):
            if any(c['type'] == self.stop_code_key and c['value'] == input_st_update.stop_id
                   for c in s.get('stop_point', {}).get('codes', [])):
                return s
        return None
