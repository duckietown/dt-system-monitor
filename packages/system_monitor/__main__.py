import sys
from .app import SystemMonitor
from .constants import APP_NAME
from .cli import get_parser
from . import __version__


def main():
    parser = get_parser()
    # ---
    # version
    if '-v' in sys.argv[1:] or '--version' in sys.argv[1:]:
        print('{} version {}\n'.format(APP_NAME, __version__))
        exit(0)
    # ---
    # parse arguments
    parsed = parser.parse_args()
    # create app and spin it
    app = SystemMonitor(parsed)
    app.start()


if __name__ == '__main__':
    main()
