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
import requests
from kirin import gtfs_realtime_pb2
import navitia_wrapper
from kirin.tasks import celery
from kirin.gtfs_rt import model_maker
import datetime
from kirin.core.model import TripUpdate, RealTimeUpdate

class InvalidFeed(Exception):
    pass

@celery.task(bind=True)
def gtfs_poller(self, config):
    logger = logging.LoggerAdapter(logging.getLogger(__name__), extra={'contributor': config['contributor']})
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

@celery.task
def gtfs_purge_trip_update(config):
    contributor = config['contributor']
    logger = logging.LoggerAdapter(logging.getLogger(__name__), extra={'contributor': contributor})
    logger.info('purge gtfs-rt trip update for %s', contributor)

    until = datetime.date.today() - datetime.timedelta(days=int(config['nb_days_to_keep']))
    logger.info('purge gtfs-rt trip update until %s', until)

    TripUpdate.remove_by_contributors_and_period(contributors=[contributor], start_date=None, end_date=until)
    logger.info('purge gtfs-rt trip update finished')

@celery.task
def gtfs_purge_rt_update(config):
    logger = logging.LoggerAdapter(logging.getLogger(__name__), extra={'connector': 'gtfs-rt'})
    logger.info('purge gtfs-rt realtime update for %s', 'gtfs-rt')

    until = datetime.date.today() - datetime.timedelta(days=int(config['nb_days_to_keep']))
    logger.info('purge gtfs-rt realtime update until %s', until)

    RealTimeUpdate.remove_by_connectors_until(connectors=['gtfs-rt'], until=until)
    logger.info('purge gtfs-rt realtime update finished')
