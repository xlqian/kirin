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

from kirin import gtfs_realtime_pb2
import navitia_wrapper
from kirin.gtfs_rt import model_maker
from kirin import app, redis
import argparse
from profiling.tracing import TracingProfiler
try:
    import cPickle as pickle
except ImportError:
    import pickle


def make_nav():
    navitia_url = app.config.get('NAVITIA_URL')
    token = app.config.get('NAVITIA_GTFS_RT_TOKEN')
    query_timeout = app.config.get('NAVITIA_QUERY_CACHE_TIMEOUT', 600)
    pubdate_timeout = app.config.get('NAVITIA_PUBDATE_CACHE_TIMEOUT', 600)
    coverage = app.config.get('NAVITIA_GTFS_RT_INSTANCE')
    return navitia_wrapper.Navitia(url=navitia_url,
                                   token=token,
                                   timeout=5,
                                   cache=redis,
                                   query_timeout=query_timeout,
                                   pubdate_timeout=pubdate_timeout).instance(coverage)


def read_proto(proto_file):
    proto = gtfs_realtime_pb2.FeedMessage()
    with open(proto_file, 'r') as f:
        content = f.read()
        proto.ParseFromString(content)
    return proto


def run(proto, nav):
    with app.app_context():
        model_maker.handle(proto, nav, app.config.get('GTFS_RT_CONTRIBUTOR'))


dump_string = """
run: 

    profiling view {}

to review your profile result

"""

description_string = """
This tool is used to profile the processing of gtfs-rt

To run the profiler:

PYTHONPATH=. KIRIN_CONFIG_FILE=dev_settings.py 
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=2 
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=cpp 
python gtfs-rt_profile.py --proto 'tripUpdates.pb' --dump test.prf
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=description_string)
    parser.add_argument('--proto', nargs='?', help='proto file')
    parser.add_argument('--dump', default='dumped_profile.prf', nargs='?', help='where to dump profiling file')

    args = parser.parse_args()

    proto = read_proto(args.proto)
    nav = make_nav()

    profiler = TracingProfiler()

    with profiler:
        run(proto, nav)

    profiler.run_viewer(title="gtfs-rt")

    with open(args.dump, 'wb') as f:
        pickle.dump((profiler.__class__, profiler.result()), f)

    print(dump_string.format(args.dump))
