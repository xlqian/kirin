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

from celery.signals import task_postrun
from kirin.helper import make_celery

from kirin import app
import requests
from kirin import gtfs_realtime_pb2
from kirin import core
import navitia_wrapper
from kirin.utils import make_rt_update
from kirin.exceptions import KirinException, InvalidArguments
from kirin.gtfs_rt.model_maker import KirinModelBuilder

celery = make_celery(app)

@task_postrun.connect
def close_session(*args, **kwargs):
    # Flask SQLAlchemy will automatically create new sessions for you from
    # a scoped session factory, given that we are maintaining the same app
    # context, this ensures tasks have a fresh session (e.g. session errors
    # won't propagate across tasks)
    model.db.session.remove()



from kirin.gtfs_rt.tasks import gtfs_poller
@celery.task(bind=True)
def poller(self):
    config = {'contributor': app.config.get('GTFS_RT_CONTRIBUTOR'),
              'navitia_url': app.config.get('NAVITIA_URL'),
              'token': app.config.get('NAVITIA_GTFS_RT_TOKEN'),
              'coverage': app.config.get('NAVITIA_GTFS_RT_INSTANCE'),
              'feed_url': app.config.get('GTFS_RT_FEED_URL'),
              }
    gtfs_poller.delay(config)

