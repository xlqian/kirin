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

from kirin.core.model import RealTimeUpdate
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


def as_date(str):
    if str is None:
        return None
    return parser.parse(str, dayfirst=False, yearfirst=True)


def to_str(date):
    return date.strftime("%Y%m%dT%H%M%S")


def headsign(str):
    """
    we remove leading 0 for the headsigns
    """
    return str.lstrip('0')


class KirinModelBuilder(object):

    def __init__(self):
        url = current_app.config['NAVITIA_URL']
        token = current_app.config.get('NAVITIA_TOKEN')
        instance = current_app.config['NAVITIA_INSTANCE']
        self.navitia = navitia_wrapper.Navitia(url=url, token=token).instance(instance)

    def build(self, raw_xml, raw_ire_id):
        """
        parse raw xml and create a real time object for kirin
        """
        created_at = datetime.datetime.now()

        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as e:
            raise InvalidArguments("invalid xml: {}".format(e.message))

        if root.tag != 'InfoRetard':
            raise InvalidArguments('{} is not a valid xml root, it must be {}'.format(root.tag, 'InfoRetard'))

        vjs = self.get_vjs(get_node(root, 'Train'))

        # for vj in vjs:

        # TODO handle also root[DernierPointDeParcoursObserve] in the modification
        vj_update = self.get_modification(get_node(root, 'TypeModification'))

        # temporary mock
        return RealTimeUpdate(created_at, vjs, vj_update, raw_ire_id)

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
            vj = model.VehicleJourney()
            vj.id = nav_vj['id']
            vjs.append(vj)

        return vjs

    def get_modification(self, xml_modification):
        """
        All ire knowledge will go here ;)
        """

        # TODO call navitia
        return None
