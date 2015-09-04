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

class StopTime(db.Model):
    """
    Stop time
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    modification_id = db.Column(postgresql.UUID, db.ForeignKey('modification.id'))
    departure = db.Column(db.DateTime, nullable=False)
    arrival = db.Column(db.DateTime, nullable=False)


class Modification(db.Model):
    """
    Modification
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    real_time_update_id = db.Column(postgresql.UUID, db.ForeignKey('real_time_update.id'))
    type = db.Column(db.Enum('add', 'delete', name='modification_type'), nullable=False)
    stop_times = db.relationship('StopTime', backref='modification')


class RealTimeUpdate(db.Model):
    """
    Real time update
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)
    vj_id = db.Column(postgresql.UUID, db.ForeignKey('vehicle_journey.id'), nullable=False)
    modification = db.relationship('Modification', uselist=False, backref='real_time_update')
