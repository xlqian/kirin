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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proto', nargs='?', help='proto file')
    parser.add_argument('--dump', default='dumped_profile.prf', nargs='?', help='dumped profiling file')

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
