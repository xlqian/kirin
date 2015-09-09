# Copyright (c) 2001-2015, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
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

import pytest

from check_utils import api_post
from kirin import app, db
from docker_wrapper import PostgresDocker


USER = 'postgres'
PWD = 'postgres'
DBNAME = 'kirin_test'

@pytest.fixture
def ire_96231():
    """
    py test fixture, to get the 96231 ire as a string
    the fixture need to be given as argument to the tests that wants to use it
    """
    import os
    file = os.path.join(os.path.dirname(__file__), 'fixtures', 'Flux-96231_2015-07-28_0.xml')
    with open(file, "r") as ire:
        return ire.read()


class Test_Ire(object):

    @classmethod
    def setup_class(cls):
        """
        Pop a temporary docker with an empty database DBNAME, we upgrade its schemas,
        then initialize the flask app with the new db adresse
        """
        cls.docker = PostgresDocker(user=USER, pwd=PWD, dbname=DBNAME)

        import os
        db_url = 'postgresql://{user}:{pwd}@{host}/{dbname}'.format(
                user=USER,
                pwd=PWD,
                host=cls.docker.ip_addr,
                dbname=DBNAME)
        # re-init the db by overriding the db_url
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        db.init_app(app)

        import flask_migrate
        app.app_context().push()
        flask_migrate.Migrate(app, db)
        migration_dir = os.path.join(os.path.dirname(__file__), '..',  'migrations')
        flask_migrate.upgrade(directory=migration_dir)

    @classmethod
    def teardown_class(cls):
        """
        Remove the temporary docker
        """
        cls.docker.exit()


    def test_wrong_ire_post(self):
        """
        simple xml post on the api
        """
        res, status = api_post('/ire', check=False, data='<bob></bob>')

        assert status == 400

        print res.get('error') == 'invalid'

    def test_ire_post(self, ire_96231):
        """
        simple xml post on the api
        """
        res = api_post('/ire', data=ire_96231)
        print res

    def test_ire_post_no_data(self):
        """
        when no data is given, we got a 400 error
        """
        tester = app.test_client()
        resp = tester.post('/ire')

        assert resp.status_code == 400
