import argparse
import logging
from configparser import ConfigParser

from .webapp import app, rebuild

parser = argparse.ArgumentParser(
    description='RAW image storage and retrieval.')

parser.add_argument('config', type=argparse.FileType())
parser.add_argument('--rebuild', help='Scan image folder and rebuild'
                    ' database', action='store_true')
args = parser.parse_args()


def main():
    config = ConfigParser()
    config.read_file(args.config)
    app.config['BASIC_AUTH_USERNAME'] = config.get('auth', 'username')
    app.config['BASIC_AUTH_PASSWORD'] = config.get('auth', 'password')
    app.config['BASE_PATH'] = config.get('storage', 'photo_path')
    app.config['DB_CSTRING'] = config.get('database', 'connection_string')

    app.logger.setLevel(logging.INFO)

    if args.rebuild:
        rebuild()

    app.run(host='0.0.0.0')
    return


if __name__ == '__main__':
    main()
