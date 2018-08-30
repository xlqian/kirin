# coding=utf-8
# Copyright (c) 2001-2018, Canal TP and/or its affiliates. All rights reserved.
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
import logging
from datetime import timedelta, datetime
from dateutil import parser
from flask.globals import current_app
from kirin.core import model
# For perf benches:
# https://artem.krylysov.com/blog/2015/09/29/benchmark-python-json-libraries/
import ujson
from kirin.exceptions import InvalidArguments, ObjectNotFound
from kirin.utils import record_internal_failure, headsigns, to_navitia_str


def get_value(dict, key, nullabe=False):
    """
    get a unique element in an xml node
    raise an exception if the element does not exists
    """
    res = dict.get(key)
    if res is None and not nullabe:
        raise InvalidArguments('invalid json, impossible to find "{key}" in json elt {elt}'.format(
            key=key, elt=ujson.dump(dict)))
    return res


def is_station(pdp):
    """
    determine if a Point de Parcours is a legit station
    :param pdp: stop_time to be checked
    :return: True if pdp is a station, False otherwise
    """
    t = pdp.get('typeArret')
    return (t is None) or (t in ['', 'CD', 'CH', 'FD', 'FH'])


def _interesting_pdp_generator(list_pdp):
    """
    filter "Points de Parcours" (corresponding to stop_times)
    :param list_pdp: an array of "Point de Parcours" (typically the one from the feed)
    :return: Filtered array
    Nota: written in a yield-fashion to switch implem if possible, but we need random access for now
    """
    res = []
    picked_one = False
    for idx, pdp in enumerate(list_pdp):
        # start consuming stop_time only at first one having a departure time
        if not picked_one and not pdp.get('horaireVoyageurDepart'):
            continue
        # exclude pdp that are not legit stations
        if not is_station(pdp):
            continue
        # stop consuming once all following stop_times are missing arrival time
        if picked_one and not pdp.get('horaireVoyageurArrivee'):
            has_following_arrival = False
            for follow_pdp in list_pdp[idx:]:
                if follow_pdp.get('horaireVoyageurArrivee') and is_station(follow_pdp):
                    has_following_arrival = True
                    break
            if not has_following_arrival:
                break

        picked_one = True
        res.append(pdp)
    return res


def as_date(s):
    if s is None:
        return None
    return parser.parse(s, dayfirst=False, yearfirst=True)


def get_navitia_stop_time(navitia_vj, stop_id):
    nav_st = next((st for st in navitia_vj['stop_times']
                  if st.get('journey_pattern_point', {})
                       .get('stop_point', {})
                       .get('id') == stop_id), None)

    # if a VJ passes several times at the same stop, we cannot know
    # perfectly which stop time to impact
    # as a first version, we only impact the first

    return nav_st


class KirinModelBuilder(object):

    def __init__(self, nav, contributor=None):
        self.navitia = nav
        self.contributor = contributor

    def build(self, rt_update):
        """
        parse raw json in the rt_update object
        and return a list of trip updates

        The TripUpdates are not yet associated with the RealTimeUpdate
        """
        try:
            json = ujson.loads(rt_update.raw_data)
        except ValueError as e:
            raise InvalidArguments("invalid json: {}".format(e.message))

        if 'nouvelleVersion' not in json:
            raise InvalidArguments('No object "nouvelleVersion" available in feed provided')

        vjs = self._get_vjs(get_value(json, 'nouvelleVersion'))
        return []

    def _get_vjs(self, json_train):
        log = logging.getLogger(__name__)
        train_numbers = headsigns(get_value(json_train, 'numeroCourse'))
        pdps = _interesting_pdp_generator(get_value(json_train, 'listePointDeParcours'))
        if not pdps:
            raise InvalidArguments('invalid json, "listePointDeParcours" has no valid stop_time in '
                                   'json elt {elt}'.format(elt=ujson.dump(json_train)))

        dates_str = [get_value(d, 'date') for d in get_value(json_train, 'listeJourRegimeDApplication')]
        date = min([as_date(d) for d in dates_str]).date()
        # to get the date of the vj we use the start/end of the vj + some tolerance
        # since the ire data and navitia data might not be synchronized
        str_time_start = get_value(get_value(pdps[0], 'horaireVoyageurDepart'), 'heureLocale')
        time_start = datetime.strptime(str_time_start, '%H:%M:%S').time()
        vj_start = datetime.combine(date, time_start)
        since = vj_start - timedelta(hours=1)
        str_time_end = get_value(get_value(pdps[-1], 'horaireVoyageurArrivee'), 'heureLocale')
        time_end = datetime.strptime(str_time_end, '%H:%M:%S').time()
        vj_end = datetime.combine(date, time_end)
        until = vj_end + timedelta(hours=1)

        vjs = {}

        for train_number in train_numbers:

            log.debug('searching for vj {} on {} in navitia'.format(train_number, vj_start))

            navitia_vjs = self.navitia.vehicle_journeys(q={
                'headsign': train_number,
                'since': to_navitia_str(since),
                'until': to_navitia_str(until),
                'depth': '2',  # we need this depth to get the stoptime's stop_area
                'show_codes': 'true'  # we need the stop_points CRCICH codes
            })

            if not navitia_vjs:
                logging.getLogger(__name__).info('impossible to find train {t} on [{s}, {u}['
                                                 .format(t=train_number,
                                                         s=since,
                                                         u=until))
                record_internal_failure('missing train', contributor=self.contributor)


            for nav_vj in navitia_vjs:
                vj = model.VehicleJourney(nav_vj, vj_start.date())
                vjs[nav_vj['id']] = vj

        if not vjs:
            raise ObjectNotFound('no train found for headsigns {}'.format(train_numbers))

        return vjs.values()
