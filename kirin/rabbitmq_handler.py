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
from kombu import BrokerConnection, Exchange, Queue, Consumer
from kombu.pools import producers, connections
import logging
from amqp.exceptions import ConnectionForced
import gevent
from kirin import task_pb2
from google.protobuf.message import DecodeError
import socket
from kirin.core.model import TripUpdate
from kirin.core.populate_pb import convert_to_gtfsrt
import gtfs_realtime_pb2
from kirin.utils import str_to_date


class RabbitMQHandler(object):
    def __init__(self, connection_string, exchange):
        self._connection = BrokerConnection(connection_string)
        self._connections = set([self._connection])  # set of connection for the heartbeat
        self._exchange = Exchange(exchange, durable=True, delivry_mode=2, type='topic')
        self._connection.connect()
        monitor_heartbeats(self._connections)

    def _get_producer(self):
        producer = producers[self._connection].acquire(block=True, timeout=2)
        self._connections.add(producer.connection)
        return producer

    def publish(self, item, contributor):
        with self._get_producer() as producer:
            producer.publish(item, exchange=self._exchange, routing_key=contributor, declare=[self._exchange])

    def info(self):
        with self._get_producer() as producer:
            res = producer.connection.info()
            if 'password' in res:
                del res['password']
            return res

    def listen_load_realtime(self, queue_name):
        log = logging.getLogger(__name__)

        def callback(body, message):
            task = task_pb2.Task()
            try:
                # `body` is of unicode type, but we need str type for
                # `ParseFromString()` to work.  It seems to work.
                # Maybe kombu estimate that, without any information,
                # the body should be something as json, and thus a
                # unicode string.  On the c++ side, I didn't manage to
                # find a way to give a content-type or something like
                # that.
                body = str(body)
                task.ParseFromString(body)
            except DecodeError as e:
                log.warn('invalid protobuf: {}'.format(str(e)))
                return

            log.info('getting a request: {}'.format(task))
            if task.action != task_pb2.LOAD_REALTIME or not task.load_realtime:
                return
            begin_date = None
            end_date = None
            if hasattr(task.load_realtime, "begin_date"):
                if task.load_realtime.begin_date:
                    begin_date = str_to_date(task.load_realtime.begin_date)

            if hasattr(task.load_realtime, "end_date"):
                if task.load_realtime.end_date:
                    end_date = str_to_date(task.load_realtime.end_date)
            feed = convert_to_gtfsrt(TripUpdate.find_by_contributor_period(task.load_realtime.contributors,
                                                                           begin_date,
                                                                           end_date),
                                     gtfs_realtime_pb2.FeedHeader.FULL_DATASET)

            with self._get_producer() as producer:
                log.info('Publishing full feed...')
                producer.publish(feed.SerializeToString(), routing_key=task.load_realtime.queue_name)
                log.info('Full feed published.')

        route = 'task.load_realtime.*'
        log.info('listening route {} on exchange {}...'.format(route, self._exchange))
        rt_queue = Queue(queue_name, routing_key=route, exchange=self._exchange, durable=False)
        with connections[self._connection].acquire(block=True) as conn:
            self._connections.add(conn)
            with Consumer(conn, queues=[rt_queue], callbacks=[callback]):
                while True:
                    try:
                        conn.drain_events(timeout=1)
                    except socket.timeout:
                        pass


def monitor_heartbeats(connections, rate=2):
    """
    launch the heartbeat of amqp, it's mostly for prevent the f@#$ firewall from droping the connection
    """
    supports_heartbeats = False
    interval = 10000
    for conn in connections:
        if conn.heartbeat and conn.supports_heartbeats:
            supports_heartbeats = True
            interval = min(conn.heartbeat / 2, interval)

    if not supports_heartbeats:
        logging.getLogger(__name__).info('heartbeat is not enabled')
        return

    logging.getLogger(__name__).info('start rabbitmq monitoring')

    def heartbeat_check():
        for conn in connections:
            if conn.connected:
                logging.getLogger(__name__).debug('heartbeat_check for %s', conn)
                try:
                    conn.heartbeat_check(rate=rate)
                except ConnectionForced:
                    #I don't know why, but pyamqp fail to detect the heartbeat
                    #So even if it fail we don't do anything
                    pass
        gevent.spawn_later(interval, heartbeat_check)

    gevent.spawn_later(interval, heartbeat_check)
