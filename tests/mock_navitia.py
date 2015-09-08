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
import json

_mock_navitia_call = {
    'vehicle_journeys/?since=20150921T153000&headsign=96231&until=20150921T173000':
        ("""{
  "vehicle_journeys":[
    {
      "name":"96231",
      "journey_pattern":{
        "name":"gare de Basel-SBB",
        "id":"journey_pattern:SCF:OCETrainTER8500010987212027-9934"
      },
      "calendars":[
        {
          "exceptions":[
            {
              "type":"remove",
              "datetime":"20150714"
            }
          ],
          "active_periods":[
            {
              "begin":"20150707",
              "end":"20151001"
            }
          ],
          "week_pattern":{
            "monday":true,
            "tuesday":true,
            "friday":true,
            "wednesday":true,
            "thursday":true,
            "sunday":false,
            "saturday":false
          }
        }
      ],
      "stop_times":[
        {
          "arrival_time":"172100",
          "headsign":"96231",
          "departure_time":"172100"
        },
        {
          "arrival_time":"173800",
          "headsign":"96231",
          "departure_time":"174000"
        },
        {
          "arrival_time":"175100",
          "headsign":"96231",
          "departure_time":"175300"
        },
        {
          "arrival_time":"181400",
          "headsign":"96231",
          "departure_time":"181600"
        },
        {
          "arrival_time":"183000",
          "headsign":"96231",
          "departure_time":"183100"
        },
        {
          "arrival_time":"183900",
          "headsign":"96231",
          "departure_time":"183900"
        }
      ],
      "validity_pattern":{
        "beginning_date":"20150706",
        "days":"000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000111001111100111110011111001111100111110011111001111100111110011111001111100111010011110"
      },
      "id":"vehicle_journey:SCFOCETrainTER87212027850001093:46155"
    }
  ]
}""", 200)
}


def mock_navitia_query(self, query, q=None):
    """
    mock the call to navitia wrapper.

    a file with the query name is looked for in the tests/fixtures dir
    """
    query_str = query
    if q:
        query_str += '?'
        sep = ''
        for param_name, param_value in q.iteritems():
            query_str += sep + param_name + '=' + param_value
            sep = '&'

    resp, status = _mock_navitia_call[query_str]
    j = json.loads(resp)

    return j, status
