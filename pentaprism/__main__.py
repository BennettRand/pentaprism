import argparse
import logging

from .webapp import app, rebuild

parser = argparse.ArgumentParser(
    description='RAW image storage and retrieval.')

parser.add_argument('username', help='Auth Username')
parser.add_argument('password', help='Auth Password')
parser.add_argument('--base', help='Base Folder', default='./.raw_images/')
parser.add_argument('--rebuild', help='Scan image folder and rebuild'
                    ' database', action='store_true')
args = parser.parse_args()


def main():
    app.config['BASIC_AUTH_USERNAME'] = args.username
    app.config['BASIC_AUTH_PASSWORD'] = args.password
    app.config['BASE_PATH'] = args.base
    app.config['DB_CSTRING'] = 'sqlite:///.test.db'

    app.logger.setLevel(logging.INFO)

    if args.rebuild:
        rebuild()

    app.run(host='0.0.0.0')
    return


if __name__ == '__main__':
    main()
