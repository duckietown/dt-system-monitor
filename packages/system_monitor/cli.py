import argparse

from .constants import \
    LOG_API_DEFAULT_DATABASE,\
    LOG_DEFAULT_SUBGROUP,\
    LOG_DEFAULT_GROUP,\
    DEFAULT_TARGET


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type',
                        required=True,
                        help="Specify a device type (e.g., duckiebot, watchtower)")
    parser.add_argument('-T',
                        '--target',
                        default=DEFAULT_TARGET,
                        help="Specify a Docker endpoint to monitor")
    parser.add_argument('--app-id',
                        required=True,
                        type=str,
                        help="ID of the API App used to authenticate the push to the server. " +
                             "Must have access to the 'data/set' API endpoint")
    parser.add_argument('--app-secret',
                        required=True,
                        type=str,
                        help="Secret of the API App used to authenticate the push to the server")
    parser.add_argument('-D',
                        '--database',
                        default=LOG_API_DEFAULT_DATABASE,
                        type=str,
                        help="Name of the logging database. Must be an existing database.")
    parser.add_argument('-G',
                        '--group',
                        default=LOG_DEFAULT_GROUP,
                        type=str,
                        help="Name of the logging group within the database")
    parser.add_argument('-S',
                        '--subgroup',
                        default=LOG_DEFAULT_SUBGROUP,
                        type=str,
                        help="Name of the logging subgroup within the database")
    parser.add_argument('-F',
                        '--filter',
                        action='append',
                        default=[],
                        nargs='*',
                        help="Specify regexes used to filter the monitored containers")
    parser.add_argument('-d',
                        '--duration',
                        required=True,
                        type=int,
                        help="Length of the analysis in seconds")
    parser.add_argument('--system',
                        default=False,
                        action='store_true',
                        help="Log system processes as well")
    parser.add_argument('-m',
                        '--notes',
                        default='(empty)',
                        type=str,
                        help="Custom notes to attach to the log")
    parser.add_argument('--debug', action='store_true',
                        default=False, help="Run in debug mode")
    parser.add_argument('-vv',
                        '--verbose',
                        dest='verbose',
                        action='store_true',
                        default=False,
                        help="Run in verbose mode")
    parser.add_argument("--no-upload", dest="no_upload", action="store_true",
                        default=False, help="Do not upload the statistics to the Duckietown server.")
    return parser
