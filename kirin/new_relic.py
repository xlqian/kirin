# coding=utf-8

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

from __future__ import absolute_import, print_function, division
import logging
import flask
import os

try:
    from newrelic import agent
except ImportError:
    logger = logging.getLogger(__name__)
    logger.exception('failure while importing newrelic')
    agent = None

def init(config_file):
    if agent and config_file and os.path.exists(config_file):
        agent.initialize(config_file)
    else:
        logger = logging.getLogger(__name__)
        logger.warn('newrelic hasn\'t been initialized')

def record_exception():
    """
    record the exception currently handled to newrelic
    """
    if agent:
        agent.record_exception()#will record the exception currently handled

def record_custom_parameter(name, value):
    """
    add a custom parameter to the current request
    """
    if agent:
        agent.add_custom_parameter(name, value)

def record_custom_event(event_type, params):
    """
    record an event
    Event doesn't share anything with request so we track the request id
    """
    if agent:
        try:
            if not params:
                params = {}
            params['kirin_request_id'] = flask.request.id
        except RuntimeError:
            pass#we are outside of a flask context :(
        try:
            agent.record_custom_event(event_type, params)
        except:
            logger = logging.getLogger(__name__)
            logger.exception('failure while reporting to newrelic')

def ignore():
    """
    the transaction will be suppressed by newrelic
    """
    if agent:
        try:
            agent.suppress_transaction_trace()
        except:
            logger = logging.getLogger(__name__)
            logger.exception('failure while suppressing transaction')

def ignore_transaction():
    """
    the transaction will be ignored by newrelic
    """
    if agent:
        try:
            agent.ignore_transaction()
        except:
            logger = logging.getLogger(__name__)
            logger.exception('failure while ignoring transaction')
