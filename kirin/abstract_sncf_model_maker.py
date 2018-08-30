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
import logging
from datetime import timedelta
from kirin.utils import record_internal_failure
from kirin.exceptions import ObjectNotFound
from abc import ABCMeta
import six
from kirin.core import model


def to_navitia_str(dt):
    """
    format a datetime to a navitia-readable str
    """
    return dt.strftime("%Y%m%dT%H%M%S")


def headsigns(str):
    """
    we remove leading 0 for the headsigns and handle the train's parity

    the parity is the number after the '/'. it gives an alternative train number

    >>> headsigns('2038')
    [u'2038']
    >>> headsigns('002038')
    [u'2038']
    >>> headsigns('002038/12')
    [u'2038', u'2012']
    >>> headsigns('2038/3')
    [u'2038', u'2033']
    >>> headsigns('2038/123')
    [u'2038', u'2123']
    >>> headsigns('2038/12345')
    [u'2038', u'12345']

    """
    h = str.lstrip('0')
    if '/' not in h:
        return [h]
    signs = h.split('/', 1)
    alternative_headsign = signs[0][:-len(signs[1])] + signs[1]
    return [signs[0], alternative_headsign]


class AbstractSNCFKirinModelBuilder(six.with_metaclass(ABCMeta, object)):

    def __init__(self, nav, contributor=None):
        self.navitia = nav
        self.contributor = contributor

    def _get_navitia_vjs(self, headsign_str, since_dt, until_dt):
        log = logging.getLogger(__name__)

        vjs = {}
        # we search with a 1-hour margin
        extended_since_dt = since_dt - timedelta(hours=1)
        extended_until_dt = until_dt + timedelta(hours=1)

        for train_number in headsigns(headsign_str):

            log.debug('searching for vj {} on {} in navitia'.format(train_number, since_dt))

            navitia_vjs = self.navitia.vehicle_journeys(q={
                'headsign': train_number,
                'since': to_navitia_str(extended_since_dt),
                'until': to_navitia_str(extended_until_dt),
                'depth': '2',  # we need this depth to get the stoptime's stop_area
                'show_codes': 'true'  # we need the stop_points CRCICH codes
            })

            if not navitia_vjs:
                logging.getLogger(__name__).info('impossible to find train {t} on [{s}, {u}['
                                                 .format(t=train_number,
                                                         s=extended_since_dt,
                                                         u=extended_until_dt))
                record_internal_failure('missing train', contributor=self.contributor)

            for nav_vj in navitia_vjs:
                vj = model.VehicleJourney(nav_vj, since_dt.date())
                vjs[nav_vj['id']] = vj

        if not vjs:
            raise ObjectNotFound('no train found for headsigns {}'.format(headsigns))

        return vjs.values()
