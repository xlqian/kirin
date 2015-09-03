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

from kirin.core.model import RealTimeObject
# For perf benches:
# http://effbot.org/zone/celementtree.htm
import xml.etree.cElementTree as ElementTree
from kirin.exceptions import InvalidArguments


def get_node(elt, node):
    """
    get a unique element in an xml node
    raise an exception if the element does not exists
    """
    res = elt.find(node)
    if res is None:
        raise InvalidArguments('invalid xml, impossible to find "{node}" in xml elt {elt}'.format(
            node=node, elt=elt.tag))
    return res


def get_vj(xml_train):
    train_number = get_node(xml_train, 'NumeroTrain')  # TODO handle parity in train number
    date = get_node(xml_train, 'DateCirculation')
    # TODO call navitia
    return None


def get_modification(xml_modification):
    """
    All ire knowledge will go here ;)
    """

    # TODO call navitia
    return None


def make_kirin_objet(raw_xml):
    """
    parse raw xml and create a real time object for kirin
    """
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError as e:
        raise InvalidArguments("invalid xml: {}".format(e.message))

    if root.tag != 'InfoRetard':
        raise InvalidArguments('{} is not a valid xml root, it must be {}'.format(root.tag, 'InfoRetard'))

    vj = get_vj(get_node(root, 'Train'))

    # TODO handle also root[DernierPointDeParcoursObserve] in the modification
    vj_update = get_modification(get_node(root, 'TypeModification'))

    # temporary mock
    return RealTimeObject()

