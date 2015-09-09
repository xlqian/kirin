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
import logging
from datetime import timedelta
from flask.globals import current_app
from dateutil import parser
from kirin.core import model

# For perf benches:
# http://effbot.org/zone/celementtree.htm
import xml.etree.cElementTree as ElementTree
import datetime
from kirin.exceptions import InvalidArguments, ObjectNotFound
import navitia_wrapper


def get_node(elt, *nodes):
    """
    get a unique element in an xml node
    raise an exception if the element does not exists
    """
    if not nodes:
        return None

    current_elt = elt
    for node in nodes:
        res = current_elt.find(node)
        if res is None:
            raise InvalidArguments('invalid xml, impossible to find "{node}" in xml elt {elt}'.format(
                node=node, elt=elt.tag))
        current_elt = res
    return res


def get_value(elt, *nodes):
    node = get_node(elt, *nodes)
    return node.text if node is not None else None


def as_date(s):
    if s is None:
        return None
    return parser.parse(s, dayfirst=False, yearfirst=True)


def to_str(date):
    return date.strftime("%Y%m%dT%H%M%S")


def headsign(str):
    """
    we remove leading 0 for the headsigns
    """
    return str.lstrip('0')


def as_bool(s):
    return s == 'true'


class KirinModelBuilder(object):

    def __init__(self, nav):
        self.navitia = nav

    def build(self, rt_update):
        """
        parse raw xml and change the rt_update object with all the IRE data
        """
        try:
            root = ElementTree.fromstring(rt_update.raw_data)
        except ElementTree.ParseError as e:
            raise InvalidArguments("invalid xml: {}".format(e.message))

        if root.tag != 'InfoRetard':
            raise InvalidArguments('{} is not a valid xml root, it must be {}'.format(root.tag, 'InfoRetard'))

        vjs = self.get_vjs(get_node(root, 'Train'))

        for vj in vjs:
            # TODO handle also root[DernierPointDeParcoursObserve] in the modification
            vj_update = self.make_vj_update(vj, get_node(root, 'TypeModification'))
            rt_update.vj_updates.append(vj_update)

    def get_vjs(self, xml_train):
        log = logging.getLogger(__name__)
        train_number = headsign(get_value(xml_train, 'NumeroTrain'))  # TODO handle parity in train number

        # to get the date of the vj we need to get the start of the vj
        vj_start_str = get_value(xml_train, 'OrigineTheoriqueTrain', 'DateHeureDepart')

        if not vj_start_str:
            raise InvalidArguments('no start date for the train {}'.format(train_number))

        vj_start = as_date(vj_start_str)
        since = vj_start - timedelta(hours=1)
        until = vj_start + timedelta(hours=1)

        log.debug('searching for vj {} on {} in navitia'.format(train_number, vj_start))

        navitia_vjs = self.navitia.vehicle_journeys(q={
            'headsign': train_number,
            'since': to_str(since),
            'until': to_str(until)
        })

        if not navitia_vjs:
            raise ObjectNotFound(
                'impossible to find train {t} on [{s}, {u}['.format(t=train_number,
                                                                    s=since,
                                                                    u=until))

        vjs = []
        for nav_vj in navitia_vjs:
            vj = model.VehicleJourney(nav_vj, vj_start.date)
            vjs.append(vj)

        return vjs

    def make_vj_update(self, vj, xml_modification):
        """
        create the VJUpdate object
        """
        vj_update = model.VJUpdate(vj=vj)

        delay = xml_modification.find('HoraireProjete')
        if delay:
            for point_aval in delay.iter('PointAval'):
                # we need only to consider the station
                if not as_bool(get_value(point_aval, 'IndicateurPRGare')):
                    continue
                stop_id = self.get_navitia_stop_id(point_aval)

                departure = None
                arrival = None
                st = model.StopTime(stop_id, departure, arrival)
                vj_update.stop_times.append(st)

        return vj_update

    def get_navitia_stop_id(self, xml_node):
        """
        get a navitia stop from an xml node
        the xml node MUST contains a CR, CI, CH tags

        it searchs in navitia for a stop_area with the external code
        CR-CI-CH
        """
        cr = get_value(xml_node, 'CRPR')
        ci = get_value(xml_node, 'CIPR')
        ch = get_value(xml_node, 'CHPR')

        nav_external_code = "{cr}-{ci}-{ch}".format(cr=cr, ci=ci, ch=ch)

        nav_stops = self.navitia.stop_areas(q={'filter': 'stop_area.has_code(CRCICH, {code})'
            .format(code=nav_external_code)})

        if not nav_stops:
            raise InvalidArguments('impossible to find stop "{}" in navitia'.format(nav_external_code))

        if len(nav_stops) > 1:
            raise InvalidArguments('too many stops found for code "{}" in navitia'.format(nav_external_code))

        stop_area = nav_stops[0]

        return stop_area['id']
