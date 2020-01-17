import argparse


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type',
                        required=True,
                        help="Specify a device type (e.g., duckiebot, watchtower)")
    parser.add_argument('-T',
                        '--target',
                        default="unix://var/run/docker.sock",
                        help="Specify a Docker endpoint to monitor")
    parser.add_argument('-F',
                        '--filter',
                        action='append',
                        default=['.*'],
                        help="Specify regexes used to filter the monitored containers")
    parser.add_argument('-d',
                        '--duration',
                        default=-1,
                        type=int,
                        help="Length of the analysis in seconds, (-1: indefinite)")
    parser.add_argument('--debug', action='store_true', default=False, help="Run in debug mode")
    parser.add_argument('-vv',
                        '--verbose',
                        dest='verbose',
                        action='store_true',
                        default=False,
                        help="Run in verbose mode")
    return parser
