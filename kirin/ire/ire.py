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
from flask.ext.restful import reqparse
import flask
from flask_restful import Resource

from kirin.core import handle
from kirin.exceptions import InvalidArguments
from model_maker import make_kirin_objet
import kirin


def _persist_ire(raw_xml):
    """
    Save the whole raw xml into the db
    """
    raw_ire_obj = kirin.core.model.RealTimeUpdate(raw_xml, connector='ire')
    kirin.core.model.db.session.add(raw_ire_obj)
    kirin.core.model.db.session.commit()
    return raw_ire_obj

def get_ire(req):
    """
    get IRE stream, for the moment, it's the raw xml
    """
    if not req.data:
        raise InvalidArguments('no ire data provided')
    return req.data


class Ire(Resource):

    def post(self):
        raw_xml = get_ire(flask.globals.request)

        # create a raw ire obj, save the raw_xml into the db
        raw_update = _persist_ire(raw_xml)

        # raw_xml is  interpreted
        kirin_obj = make_kirin_objet(raw_xml, raw_update.id)
        # TODO: commit the kirin obj? and where?

        handle(kirin_obj)

        return 'OK', 200
