# Copyright (c) 2001-2017, Canal TP and/or its affiliates. All rights reserved.
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

import flask
from flask.globals import current_app
from flask_restful import Resource
from google.protobuf.message import DecodeError
from kirin import core
from kirin.core import model
from kirin.exceptions import KirinException, InvalidArguments
from kirin.utils import make_navitia_wrapper, make_rt_update
from kirin.gtfs_rt.model_maker import KirinModelBuilder
import navitia_wrapper


def _get_gtfs_rt(req):
    if not req.data:
        raise InvalidArguments('no gtfs_rt data provided')
    return req.data


class GtfsRT(Resource):

    def __init__(self):
        url = current_app.config['NAVITIA_URL']
        token = current_app.config.get('NAVITIA_GTFS_RT_TOKEN')
        instance = current_app.config['NAVITIA_GTFS_RT_INSTANCE']
        self.navitia_wrapper = navitia_wrapper.Navitia(url=url, token=token).instance(instance)
        self.navitia_wrapper.timeout = current_app.config.get('NAVITIA_TIMEOUT', 5)
        self.contributor = current_app.config['GTFS_RT_CONTRIBUTOR']

    def post(self):
        raw_proto = _get_gtfs_rt(flask.globals.request)

        from kirin import gtfs_realtime_pb2
        # create a raw gtfs-rt obj, save the raw protobuf into the db
        proto = gtfs_realtime_pb2.FeedMessage()
        try:
            proto.ParseFromString(raw_proto)
        except DecodeError:
            raise InvalidArguments('invalid protobuf')

        data = str(proto)  # temp, for the moment, we save the protobuf as text
        rt_update = make_rt_update(data, 'gtfs-rt')
        try:
            trip_updates = KirinModelBuilder(self.navitia_wrapper, self.contributor).build(rt_update,
                                                                                           data=proto)
        except KirinException as e:
            rt_update.status = 'KO'
            rt_update.error = e.data['error']
            model.db.session.add(rt_update)
            model.db.session.commit()
            raise
        except Exception as e:
            rt_update.status = 'KO'
            rt_update.error = e.message
            model.db.session.add(rt_update)
            model.db.session.commit()
            raise

        core.handle(rt_update, trip_updates, self.contributor)

        return 'OK', 200
