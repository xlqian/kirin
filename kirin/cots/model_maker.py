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

from __future__ import absolute_import, print_function, unicode_literals, division
from datetime import datetime
from dateutil import parser
from flask.globals import current_app
from kirin.abstract_sncf_model_maker import AbstractSNCFKirinModelBuilder
# For perf benches:
# https://artem.krylysov.com/blog/2015/09/29/benchmark-python-json-libraries/
import ujson
from kirin.exceptions import InvalidArguments, ObjectNotFound


def get_value(sub_json, key, nullable=False):
    """
    get a unique element in an json dict
    raise an exception if the element does not exists
    """
    res = sub_json.get(key)
    if res is None and not nullable:
        raise InvalidArguments('invalid json, impossible to find "{key}" in json dict {elt}'.format(
            key=key, elt=ujson.dump(sub_json)))
    return res


def is_station(pdp):
    """
    determine if a Point de Parcours is a legit station
    :param pdp: stop_time to be checked
    :return: True if pdp is a station, False otherwise
    """
    t = get_value(pdp, 'typeArret', nullable=True)
    return (t is None) or (t in ['', 'CD', 'CH', 'FD', 'FH'])


def _interesting_pdp_generator(list_pdp):
    """
    Filter "Points de Parcours" (corresponding to stop_times) to get only the relevant ones from
    a Navitia's perspective (stations, where travelers can hop on or hop off)
    Context: COTS may contain operating informations, useless for traveler
    :param list_pdp: an array of "Point de Parcours" (typically the one from the feed)
    :return: Filtered array
    Note: written in a yield-fashion to switch implem if possible, but we need random access for now
    """
    res = []
    picked_one = False
    for idx, pdp in enumerate(list_pdp):
        # start consuming stop_time only at the first one with a departure time
        if not picked_one and not get_value(pdp, 'horaireVoyageurDepart', nullable=True):
            continue
        # exclude pdp that are not legit stations
        if not is_station(pdp):
            continue
        # exclude pdp that have no departure nor arrival time
        if not get_value(pdp, 'horaireVoyageurDepart', nullable=True) and \
                not get_value(pdp, 'horaireVoyageurArrivee', nullable=True):
            continue
        # stop consuming once all following stop_times are missing arrival time
        # * if a stop only has departure time, travelers can only hop in, but if they are be able to
        #   hop off later because some stop_time has arrival time then the current stop_time is useful,
        #   so we keep current stop_time.
        # * if no stop_time has arrival time anymore, then stop_times are useless as traveler cannot
        #   hop off, so no point hopping in anymore, so we remove all the stop_times until the end
        #   (should not happen in practice).
        if picked_one and not get_value(pdp, 'horaireVoyageurArrivee', nullable=True):
            has_following_arrival = any(
                get_value(follow_pdp, 'horaireVoyageurArrivee', nullable=True) and is_station(follow_pdp)
                for follow_pdp in list_pdp[idx:])
            if not has_following_arrival:
                break

        picked_one = True
        res.append(pdp)
    return res


def as_date(s):
    if s is None:
        return None
    return parser.parse(s, dayfirst=False, yearfirst=True)


class KirinModelBuilder(AbstractSNCFKirinModelBuilder):

    def __init__(self, nav, contributor=None):
        super(KirinModelBuilder, self).__init__(nav, contributor)

    def build(self, rt_update):
        """
        parse raw json in the rt_update object
        and return a list of trip updates

        The TripUpdates are not yet associated with the RealTimeUpdate

        Most of the realtime information we parse is contained in 'nouvelleVersion' sub-object
        (see fixtures and documentation)
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
        train_numbers = get_value(json_train, 'numeroCourse')
        pdps = _interesting_pdp_generator(get_value(json_train, 'listePointDeParcours'))
        if not pdps:
            raise InvalidArguments('invalid json, "listePointDeParcours" has no valid stop_time in '
                                   'json elt {elt}'.format(elt=ujson.dump(json_train)))

        dates_str = [get_value(d, 'date') for d in get_value(json_train, 'listeJourRegimeDApplication')]
        date = min([as_date(d) for d in dates_str]).date()
        str_time_start = get_value(get_value(pdps[0], 'horaireVoyageurDepart'), 'heureLocale')
        time_start = datetime.strptime(str_time_start, '%H:%M:%S').time()
        vj_start = datetime.combine(date, time_start)
        str_time_end = get_value(get_value(pdps[-1], 'horaireVoyageurArrivee'), 'heureLocale')
        time_end = datetime.strptime(str_time_end, '%H:%M:%S').time()
        vj_end = datetime.combine(date, time_end)

        return self._get_navitia_vjs(train_numbers, vj_start, vj_end)

