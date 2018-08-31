# coding=utf-8
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
import itertools
import logging
from datetime import datetime
from dateutil import parser
from flask.globals import current_app

from kirin.abstract_sncf_model_maker import AbstractSNCFKirinModelBuilder, get_navitia_stop_time_sncf
from kirin.core import model
# For perf benches:
# http://effbot.org/zone/celementtree.htm
import xml.etree.cElementTree as ElementTree
from kirin.exceptions import InvalidArguments
from kirin.utils import record_internal_failure


def get_node(elt, xpath, nullable=False):
    """
    get a unique element in an xml node
    raise an exception if the element does not exists
    """
    res = elt.find(xpath)
    if res is None and not nullable:
        raise InvalidArguments('invalid xml, impossible to find "{node}" in xml elt {elt}'.format(
            node=xpath, elt=elt.tag))
    return res


def get_value(elt, xpath, nullable=False):
    node = get_node(elt, xpath, nullable)
    return node.text if node is not None else None


def as_date(s):
    if s is None:
        return None
    return parser.parse(s, dayfirst=True, yearfirst=False)


def as_duration(s):
    """
    return a string formated like 'HH:MM' to a timedelta
    >>> as_duration(None)

    >>> as_duration("12:45")
    datetime.timedelta(0, 45900)
    >>> as_duration("bob")
    Traceback (most recent call last):
    ValueError: time data 'bob' does not match format '%H:%M'
    """
    if s is None:
        return None
    d = datetime.strptime(s, '%H:%M')
    return d - datetime.strptime('00:00', '%H:%M')


def as_bool(s):
    return s == 'true'


def get_navitia_stop_time(navitia_vj, stop_id):
    nav_st = next((st for st in navitia_vj['stop_times']
                  if st.get('journey_pattern_point', {})
                       .get('stop_point', {})
                       .get('id') == stop_id), None)

    # if a VJ passes several times at the same stop, we cannot know
    # perfectly which stop time to impact
    # as a first version, we only impact the first

    return nav_st


class KirinModelBuilder(AbstractSNCFKirinModelBuilder):

    def __init__(self, nav, contributor=None):
        super(KirinModelBuilder, self).__init__(nav, contributor)

    def build(self, rt_update):
        """
        parse raw xml in the rt_update object
        and return a list of trip updates

        The TripUpdates are not yet associated with the RealTimeUpdate
        """
        try:
            root = ElementTree.fromstring(rt_update.raw_data)
        except ElementTree.ParseError as e:
            raise InvalidArguments("invalid xml: {}".format(e.message))

        if root.tag != 'InfoRetard':
            raise InvalidArguments('{} is not a valid xml root, it must be "InfoRetard"'.format(root.tag))

        vjs = self._get_vjs(get_node(root, 'Train'))

        # TODO handle also root[DernierPointDeParcoursObserve] in the modification
        trip_updates = [self._make_trip_update(vj, get_node(root, 'TypeModification')) for vj in vjs]

        return trip_updates

    def _get_vjs(self, xml_train):
        train_numbers = get_value(xml_train, 'NumeroTrain')

        # to get the date of the vj we use the start/end of the vj + some tolerance
        # since the ire data and navitia data might not be synchronized
        vj_start = as_date(get_value(xml_train, 'OrigineTheoriqueTrain/DateHeureDepart'))
        vj_end = as_date(get_value(xml_train, 'TerminusTheoriqueTrain/DateHeureTerminus'))

        return self._get_navitia_vjs(train_numbers, vj_start, vj_end)

    def _make_trip_update(self, vj, xml_modification):
        """
        create the TripUpdate object
        """
        trip_update = model.TripUpdate(vj=vj)
        trip_update.contributor = self.contributor

        delay = xml_modification.find('HoraireProjete')
        if delay:
            trip_update.status = 'update'
            for downstream_point in delay.iter('PointAval'):
                # we need only to consider the station
                if not as_bool(get_value(downstream_point, 'IndicateurPRGare')):
                    continue
                nav_st, log_dict = self._get_navitia_stop_time(downstream_point, vj.navitia_vj)
                if log_dict:
                    record_internal_failure(log_dict['log'], contributor=self.contributor)
                    log_dict.update({'contributor': self.contributor})
                    logging.getLogger(__name__).info('metrology', extra=log_dict)

                if nav_st is None:
                    continue

                nav_stop = nav_st.get('stop_point', {})

                dep_delay, dep_status = self._get_delay(downstream_point.find('TypeHoraire/Depart'))
                arr_delay, arr_status = self._get_delay(downstream_point.find('TypeHoraire/Arrivee'))

                message = get_value(downstream_point, 'MotifExterne', nullable=True)
                st_update = model.StopTimeUpdate(nav_stop, departure_delay=dep_delay, arrival_delay=arr_delay,
                                                 dep_status=dep_status, arr_status=arr_status, message=message)
                trip_update.stop_time_updates.append(st_update)

        removal = xml_modification.find('Suppression')
        if removal:
            xml_prdebut = removal.find('PRDebut')
            if get_value(removal, 'TypeSuppression') == 'T':
                trip_update.status = 'delete'
                trip_update.stop_time_updates = []
            elif get_value(removal, 'TypeSuppression') == 'P':
                # it's a partial delete
                trip_update.status = 'update'
                deleted_points = itertools.chain([removal.find('PRDebut')],
                                                 removal.iter('PointSupprime'),
                                                 [removal.find('PRFin')])
                for deleted_point in deleted_points:
                    # we need only to consider the stations
                    if not as_bool(get_value(deleted_point, 'IndicateurPRGare')):
                        continue
                    nav_st, log_dict = self._get_navitia_stop_time(deleted_point, vj.navitia_vj)
                    if log_dict:
                        record_internal_failure(log_dict['log'], contributor=self.contributor)
                        log_dict.update({'contributor': self.contributor})
                        logging.getLogger(__name__).info('metrology', extra=log_dict)

                    if nav_st is None:
                        continue

                    nav_stop = nav_st.get('stop_point', {})

                    # if the <Depart>/<Arrivee> tags are there, the departure/arrival has been deleted
                    # regardless of the <Etat> tag
                    dep_deleted = deleted_point.find('TypeHoraire/Depart') is not None
                    arr_deleted = deleted_point.find('TypeHoraire/Arrivee') is not None

                    dep_status = 'delete' if dep_deleted else 'none'
                    arr_status = 'delete' if arr_deleted else 'none'

                    message = get_value(deleted_point, 'MotifExterne', nullable=True)
                    st_update = model.StopTimeUpdate(nav_stop, dep_status=dep_status, arr_status=arr_status,
                                                     message=message)
                    trip_update.stop_time_updates.append(st_update)

            if xml_prdebut:
                trip_update.message = get_value(xml_prdebut, 'MotifExterne', nullable=True)

        return trip_update

    @staticmethod
    def _get_navitia_stop_time(downstream_point, nav_vj):
        """
        get a navitia stop from an xml node
        the xml node MUST contains a CR, CI, CH tags

        it searchs in the vj's stops for a stop_area with the external code
        CR-CI-CH
        we also return error messages as 'missing stop point', 'duplicate stops'
        """
        return get_navitia_stop_time_sncf(cr=get_value(downstream_point, 'CRPR'),
                                          ci=get_value(downstream_point, 'CIPR'),
                                          ch=get_value(downstream_point, 'CHPR'),
                                          nav_vj=nav_vj)

    @staticmethod
    def _get_delay(xml):
        """
        get the delay from IRE

        the xml is like:
        <Depart or Arrivee>
            <Etat>Retard</Etat>
            <DateHeureTheorique>21/09/2015 17:40:30</DateHeureTheorique>
            <DateHeureProjete>21/09/2015 17:55:30</DateHeureProjete>
            <EcartInterne>00:15</EcartInterne>
            <EcartExterne>00:15</EcartExterne>
        </Depart or Arrivee>

        For coherence purpose, we don't want to take the projected datetime ('DateHeureProjete'),
        since navitia may have a different schedule than IRE

        We only read the public delay ('EcartExterne') and the new datetime will be computed during the
        merge (in the handler) from the base navitia schedule and the ire date

        Note: if the XML is not here, or if the state ('Etat') is deleted ('supprimé')
        we consider that we do not have any information, thus the status is set to 'none'

        returns:
        * the delay
        * the status
        """
        if xml is None or get_value(xml, 'Etat') == u'supprimé' or xml.find('EcartExterne') is None:
            return None, 'none'

        return as_duration(get_value(xml, 'EcartExterne')), 'update'
