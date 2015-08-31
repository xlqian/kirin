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

from kirin import resources, ire
import flask_restful

from kirin import app

#we always want pretty json
flask_restful.representations.json.settings = {'indent': 4}

api = flask_restful.Api(app, catch_all_404s=True)
api.app.url_map.strict_slashes = False

api.add_resource(resources.Index,
                 '/',
                 endpoint='index')

api.add_resource(resources.Status,
                 '/status',
                 endpoint='status')

api.add_resource(ire.Ire,
                 '/ire',
                 endpoint='ire')

@app.errorhandler(Exception)
def error_handler(exception):
    """
    log all exceptions not catch before
    """
    app.logger.exception('')
