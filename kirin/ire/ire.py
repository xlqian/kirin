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
import flask
from flask.globals import current_app

from kirin.abstract_sncf_resource import AbstractSNCFResource
from kirin.exceptions import InvalidArguments
from kirin.utils import make_navitia_wrapper
from model_maker import KirinModelBuilder


def get_ire(req):
    """
    get IRE stream, for the moment, it's the raw xml
    """
    if not req.data:
        raise InvalidArguments('no ire data provided')
    return req.data


class Ire(AbstractSNCFResource):

    def __init__(self):
        super(Ire, self).__init__(make_navitia_wrapper(),
                                  current_app.config.get('NAVITIA_TIMEOUT', 5),
                                  current_app.config['CONTRIBUTOR'])

    def post(self):
        raw_xml = get_ire(flask.globals.request)

        return self.process_post(raw_xml, KirinModelBuilder, 'ire')
