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
from kombu import BrokerConnection, Exchange
from kombu.pools import producers, connections
import logging
from amqp.exceptions import ConnectionForced
import gevent


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
        if not self._is_active:
            return {}
        with self._get_producer() as producer:
            res = producer.connection.info()
            if 'password' in res:
                del res['password']
            return res


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
