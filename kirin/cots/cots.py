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
from flask_restful import Resource

from kirin import core
from kirin.core import model
from kirin.exceptions import KirinException, InvalidArguments
from kirin.utils import make_navitia_wrapper, make_rt_update, record_call
#from model_maker import KirinModelBuilder #TODO create and use model_maker.py
from datetime import datetime
import logging


def get_cots(req):
    """
    get COTS stream, for the moment, it's the raw json
    """
    if not req.data:
        raise InvalidArguments('no COTS data provided')
    return req.data


class Cots(Resource):

    def __init__(self):
        self.navitia_wrapper = make_navitia_wrapper()
        self.navitia_wrapper.timeout = current_app.config.get('NAVITIA_TIMEOUT', 5)
        self.contributor = current_app.config['COTS_CONTRIBUTOR']

    def post(self):
        raw_json = get_cots(flask.globals.request)

        # create a raw cots obj, save the raw_json into the db
        rt_update = make_rt_update(raw_json, 'cots', contributor=self.contributor)
        start_datetime = datetime.utcnow()
        try:
            # assuming UTF-8 encoding for all cots input
            rt_update.raw_data = rt_update.raw_data.encode('utf-8')

            # raw_json is interpreted
            trip_updates = [] #TODO create and use model_maker.py
            #trip_updates = KirinModelBuilder(self.navitia_wrapper, self.contributor).build(rt_update)
            record_call('OK', contributor=self.contributor)
        except KirinException as e:
            rt_update.status = 'KO'
            rt_update.error = e.data['error']
            model.db.session.add(rt_update)
            model.db.session.commit()
            record_call('failure', reason=str(e), contributor=self.contributor)
            raise
        except Exception as e:
            rt_update.status = 'KO'
            rt_update.error = e.message
            model.db.session.add(rt_update)
            model.db.session.commit()
            record_call('failure', reason=str(e), contributor=self.contributor)
            raise

        _, log_dict = core.handle(rt_update, trip_updates, current_app.config['COTS_CONTRIBUTOR'])
        duration = (datetime.utcnow() - start_datetime).total_seconds()
        log_dict.update({'duration': duration})
        record_call('Simple feed publication', **log_dict)
        logging.getLogger(__name__).info('Simple feed publication', extra=log_dict)

        return 'OK', 200
