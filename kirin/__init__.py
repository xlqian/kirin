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
import os
from kirin import exceptions
from kirin.rabbitmq_handler import RabbitMQHandler

VERSION = '0.2.1'

#remplace blocking method by a non blocking equivalent
#this enable us to use gevent for launching background task
#Note: there is a conflict between py.test and gevent
# http://stackoverflow.com/questions/8774958/keyerror-in-module-threading-after-a-successful-py-test-run
# so we need to remove threading from the import
import sys
if 'threading' in sys.modules:
    print 'deleting threading from import'
    del sys.modules['threading']
#end of conflict's patch
from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging.config
import sys

app = Flask(__name__)
app.config.from_object('kirin.default_settings')
if 'KIRIN_CONFIG_FILE' in os.environ:
    app.config.from_envvar('KIRIN_CONFIG_FILE')

from kirin.core import model
db = model.db
db.init_app(app)

if 'LOGGER' in app.config:
    logging.config.dictConfig(app.config['LOGGER'])
else:  # Default is std out
    handler = logging.StreamHandler(stream=sys.stdout)
    app.logger.addHandler(handler)
    app.logger.setLevel('INFO')

rabbitmq_handler = RabbitMQHandler(app.config['RABBITMQ_CONNECTION_STRING'],
                                   app.config['EXCHANGE'])

import kirin.api
