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
from datetime import timedelta
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref, deferred
from sqlalchemy.ext.orderinglist import ordering_list
from flask_sqlalchemy import SQLAlchemy
import datetime
import sqlalchemy
db = SQLAlchemy()

# default name convention for db constraints (when not specified), for future alembic updates
meta = sqlalchemy.schema.MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })

#force the server to use UTC time for each connection
def set_utc_on_connect(dbapi_con, con_record):
    c = dbapi_con.cursor()
    c.execute("SET timezone='utc'")
    c.close()
sqlalchemy.event.listen(sqlalchemy.pool.Pool, 'connect', set_utc_on_connect)


def gen_uuid():
    """
    Generate uuid as string
    """
    import uuid
    return str(uuid.uuid4())


class TimestampMixin(object):
    created_at = db.Column(db.DateTime(), default=datetime.datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(), default=None, onupdate=datetime.datetime.utcnow)

ModificationType = db.Enum('add', 'delete', 'update', 'none', name='modification_type')


class VehicleJourney(db.Model):
    """
    Vehicle Journey
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    navitia_trip_id = db.Column(db.Text, nullable=False)
    circulation_date = db.Column(db.Date, nullable=False)  # in local timezone

    __table_args__ = (db.UniqueConstraint('navitia_trip_id', 'circulation_date', name='vehicle_journey_navitia_trip_id_circulation_date_idx'),)

    def __init__(self, navitia_vj, circulation_date):
        self.id = gen_uuid()
        if 'trip' in navitia_vj and 'id' in navitia_vj['trip']:
            self.navitia_trip_id = navitia_vj['trip']['id']
        self.circulation_date = circulation_date
        self.navitia_vj = navitia_vj  # Not persisted

    @classmethod
    def purge(cls, until):
        for vj in cls.query.filter(cls.circulation_date < until):
            db.session.delete(vj)


class StopTimeUpdate(db.Model, TimestampMixin):
    """
    Stop time
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    trip_update_id = db.Column(postgresql.UUID, db.ForeignKey('trip_update.vj_id'), nullable=False)

    # stop time's order in the vj
    order = db.Column(db.Integer, nullable=False)

    stop_id = db.Column(db.Text, nullable=False)

    message = db.Column(db.Text, nullable=True)

    # Note: for departure (and arrival), we store its datetime ('departure' or 'arrival')
    # and the delay to be able to handle the base navitia schedule changes
    departure = db.Column(db.DateTime, nullable=True)
    departure_delay = db.Column(db.Interval, nullable=True)
    departure_status = db.Column(ModificationType, nullable=False, default='none')

    arrival = db.Column(db.DateTime, nullable=True)
    arrival_delay = db.Column(db.Interval, nullable=True)
    arrival_status = db.Column(ModificationType, nullable=False, default='none')

    def __init__(self, navitia_stop,
                 departure=None, arrival=None,
                 departure_delay=None, arrival_delay=None,
                 dep_status='none', arr_status='none',
                 message=None):
        self.id = gen_uuid()
        self.navitia_stop = navitia_stop
        self.stop_id = navitia_stop['id']
        self.departure_status = dep_status
        self.arrival_status = arr_status
        self.departure_delay = departure_delay
        self.arrival_delay = arrival_delay
        self.departure = departure
        self.arrival = arrival
        self.message = message

    def update_departure(self, time=None, delay=None, status=None):
        if time:
            self.departure = time
        if delay is not None:
            self.departure_delay = delay
        if status:
            self.departure_status = status

    def update_arrival(self, time=None, delay=None, status=None):
        if time:
            self.arrival = time
        if delay is not None:
            self.arrival_delay = delay
        if status:
            self.arrival_status = status


associate_realtimeupdate_tripupdate = db.Table('associate_realtimeupdate_tripupdate',
                                    db.metadata,
                                    db.Column('real_time_update_id', postgresql.UUID, db.ForeignKey('real_time_update.id')),
                                    db.Column('trip_update_id', postgresql.UUID, db.ForeignKey('trip_update.vj_id')),
                                    db.PrimaryKeyConstraint('real_time_update_id', 'trip_update_id', name='associate_realtimeupdate_tripupdate_pkey')
)


class TripUpdate(db.Model, TimestampMixin):
    """
    Update information for Vehicule Journey
    """
    vj_id = db.Column(postgresql.UUID, db.ForeignKey('vehicle_journey.id'), nullable=False, primary_key=True)
    status = db.Column(ModificationType, nullable=False, default='none')
    vj = db.relationship('VehicleJourney', uselist=False, lazy='joined',
                         backref=backref('trip_update', cascade='all, delete-orphan', single_parent=True),
                         cascade='all, delete-orphan', single_parent=True)
    message = db.Column(db.Text, nullable=True)
    contributor = db.Column(db.Text, nullable=True)
    stop_time_updates = db.relationship('StopTimeUpdate', backref='trip_update', lazy='joined',
                                        order_by="StopTimeUpdate.order",
                                        collection_class=ordering_list('order'),
                                        cascade='all, delete-orphan')

    def __init__(self, vj=None, status='none', contributor=None):
        self.created_at = datetime.datetime.utcnow()
        self.vj = vj
        self.status = status
        self.contributor = contributor

    def __repr__(self):
        return '<TripUpdate %r>' % self.vj_id

    @classmethod
    def find_by_dated_vj(cls, navitia_trip_id, vj_circulation_date):
        return cls.query.join(VehicleJourney).filter(VehicleJourney.navitia_trip_id == navitia_trip_id,
                                              VehicleJourney.circulation_date == vj_circulation_date).first()

    @classmethod
    def find_by_contributor_period(cls, contributors, start_date=None, end_date=None):
        query = cls.query.filter(cls.contributor.in_(contributors))
        if start_date:
            query = query.filter(sqlalchemy.text("vehicle_journey_1.circulation_date >= '{start_date}'".
                                 format(start_date=start_date)))
        if end_date:
            query = query.filter(sqlalchemy.text("vehicle_journey_1.circulation_date <= '{end_date}'".
                                 format(end_date=end_date)))
        return query.all()

    @classmethod
    def remove_by_contributors_and_period(cls, contributors, start_date=None, end_date=None):
        trip_updates_to_remove = cls.find_by_contributor_period(contributors=contributors,
                                                                start_date=start_date,
                                                                end_date=end_date)
        for t in trip_updates_to_remove:
            f = sqlalchemy.text("associate_realtimeupdate_tripupdate.trip_update_id='{}'".format(t.vj_id))
            db.session.query(associate_realtimeupdate_tripupdate).filter(f).delete(synchronize_session=False)
            db.session.delete(t)

        db.session.commit()

    def find_stop(self, stop_id):
        #TODO: we will need to handle vj who deserve the same stop multiple times
        for st in self.stop_time_updates:
            if st.stop_id == stop_id:
                return st
        return None


class RealTimeUpdate(db.Model, TimestampMixin):
    """
    Real Time Update received from POST request

    This model is used to persist the raw_data: .
    A real time update object will be constructed from the raw_xml then the
    constructed real_time_update's id should be affected to TripUpdate's real_time_update_id

    There is a one-to-many relationship between RealTimeUpdate and TripUpdate.
    """
    id = db.Column(postgresql.UUID, default=gen_uuid, primary_key=True)
    received_at = db.Column(db.DateTime, nullable=False)
    connector = db.Column(db.Enum('ire', 'gtfs-rt', name='connector_type'), nullable=False)
    status = db.Column(db.Enum('OK', 'KO', 'pending', name='rt_status'), nullable=True)
    error = db.Column(db.Text, nullable=True)
    raw_data = deferred(db.Column(db.Text, nullable=True))
    contributor = db.Column(db.Text, nullable=True)

    trip_updates = db.relationship("TripUpdate", secondary=associate_realtimeupdate_tripupdate, cascade='all',
                                   lazy='select', backref=backref('real_time_updates', cascade='all'))

    __table_args__ = (db.Index('realtime_update_created_at', 'created_at'),)

    def __init__(self, raw_data, connector, contributor, status=None, error=None, received_at=None):
        self.id = gen_uuid()
        self.raw_data = raw_data
        self.connector = connector
        self.status = status
        self.error = error
        self.contributor = contributor
        self.received_at = received_at if received_at else datetime.datetime.utcnow()

    @classmethod
    def get_last_update_by_contributor(cls):
        from kirin import app
        result = {}
        contributor = [app.config['CONTRIBUTOR'], app.config['GTFS_RT_CONTRIBUTOR']]
        for c in contributor:
            row = db.session.query(db.func.max(cls.created_at)) \
                              .filter(cls.contributor == c).one()
            result[c] = row[0].strftime('%Y-%m-%dT%H:%M:%SZ')
        return result

    @classmethod
    def remove_by_connectors_until(cls, connectors, until):
        sub_query = db.session.query(associate_realtimeupdate_tripupdate.c.real_time_update_id)
        query = cls.query.\
            filter(cls.connector.in_(connectors)).\
            filter(cls.created_at <= until).\
            filter(cls.id.notin_(sub_query))
        query.delete(synchronize_session=False)
        db.session.commit()

