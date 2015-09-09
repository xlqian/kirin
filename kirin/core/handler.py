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

from model import RealTimeUpdate

def handle(real_time_update):
    """
    receive a RealTimeUpdate with at least one VehicleJourneyUpdate filled with the data received
    by the connector. each VehicleJourneyUpdate is associated with the VehicleJourney returned by jormugandr
    """
    if not real_time_update or not hasattr(real_time_update, 'vj_updates'):
        raise TypeError()

    for vj_update in real_time_update.vj_updates:
        pass
        #find if there already a row in db

        #merge the theoric, the current realtime, and the new relatime

        #produce a gtfs from that and send it

    feed = convert_to_gtfsrt(real_time_update)
    publish(feed)
    return real_time_update


def convert_to_gtfsrt(real_time_update):
    return None

def publish(feed):
    pass
