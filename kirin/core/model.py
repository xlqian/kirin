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

from sqlalchemy.dialects import postgresql
from flask_sqlalchemy import SQLAlchemy
import datetime
db = SQLAlchemy()


def gen_uuid():
    """
    Generate uuid as string
    """
    import uuid
    return str(uuid.uuid4())


class VehicleJourney(db.Model):
    """
    Vehicle Journey
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    navitia_id = db.Column(db.Text, nullable=False)
    circulation_date = db.Column(db.Date, nullable=False)

    def __init__(self, navitia_id, circulation_date):
        self.id = gen_uuid()
        self.navitia_id = navitia_id
        self.circulation_date = circulation_date


class StopTime(db.Model):
    """
    Stop time
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    modification_id = db.Column(postgresql.UUID, db.ForeignKey('modification.id'))
    departure = db.Column(db.DateTime, nullable=False)
    arrival = db.Column(db.DateTime, nullable=False)

    def __init__(self, departure, arrival):
        self.id = gen_uuid()
        self.departure = departure
        self.arrival = arrival


class Modification(db.Model):
    """
    Modification
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    real_time_update_id = db.Column(postgresql.UUID, db.ForeignKey('vj_update.id'))
    type = db.Column(db.Enum('add', 'delete', name='modification_type'), nullable=False)
    stop_times = db.relationship('StopTime', backref='modification')

    def __init__(self, modification_type, stop_times):
        self.id = gen_uuid()
        self.type = modification_type
        self.stop_times = stop_times

class VjUpdate(db.Model):
    """
    Update information for Vehicule Journey
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)
    vj_id = db.Column(postgresql.UUID, db.ForeignKey('vehicle_journey.id'), nullable=False)
    modification = db.relationship('Modification', uselist=False, backref='real_time_update')
    raw_data_id = db.Column(postgresql.UUID, db.ForeignKey('real_time_update.id'), nullable=False)

    def __init__(self, created_at, vj_id, modification, raw_data_id):
        self.id = gen_uuid()
        self.created_at = created_at
        self.vj_id = vj_id
        self.modification = modification
        self.raw_data_id = raw_data_id


class RealTimeUpdate(db.Model):
    """
    Real Time Update received from POST request

    This model is used to persist the raw_data: .
    A real time update object will be constructed from the raw_xml then the
    constructed real_time_update's id should be affected to VjUpdate's real_time_update_id

    There is a one-to-many relationship between RealTimeUpdate and VjUpdate.
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    received_at = db.Column(db.DateTime, nullable=False)
    contributor = db.Column(db.Text, nullable=False)
    connector = db.Column(db.Enum('ire', 'gtfsrt', name='connector_type'))
    status = db.Column(db.Enum('OK', 'KO', 'pending', name='rt_status'), nullable=False)
    error = db.Column(db.Text, nullable=True)
    raw_data = db.Column(db.Text, nullable=False)
    vj_updates = db.relationship('VjUpdate')

    def __init__(self, raw_data, contributor, connector, status, error='', received_at=datetime.datetime.now()):
        self.id = gen_uuid()
        self.raw_data = raw_data
        self.contributor = contributor
        self.connector = connector
        self.status = status
        self.error = error
        self.received_at = received_at

