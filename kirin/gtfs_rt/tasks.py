# Copyright (c) 2001-2014, Canal TP and/or its affiliates. All rights reserved.
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
from kirin.core import model

from kirin import app
import requests
from kirin import gtfs_realtime_pb2
from kirin import core
import navitia_wrapper
from kirin.utils import make_rt_update
from kirin.exceptions import KirinException, InvalidArguments
from kirin.gtfs_rt.model_maker import KirinModelBuilder
from kirin.tasks import celery
from kirin.gtfs_rt import model_maker
from google.protobuf.message import DecodeError


class InvalidFeed(Exception):
    pass

@celery.task(bind=True)
def gtfs_poller(self, config):
    logger =  logging.LoggerAdapter(logging.getLogger(__name__), extra={'contributor': config['contributor']})
    logger.debug('polling of %s', config['feed_url'])
    response = requests.get(config['feed_url'], timeout=config.get('timeout', 1))
    response.raise_for_status()

    nav = navitia_wrapper.Navitia(url=config['navitia_url'], token=config['token'])\
                         .instance(config['coverage'])
    nav.timeout = 5

    proto = gtfs_realtime_pb2.FeedMessage()
    proto.ParseFromString(response.content)
    model_maker.handle(proto, nav, config['contributor'])
    logger.debug('gtfsrt polling finished')

