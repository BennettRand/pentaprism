import argparse

from .webapp import app

parser = argparse.ArgumentParser(
    description='RAW image storage and retrieval.')

parser.add_argument('username', help='Auth Username')
parser.add_argument('password', help='Auth Password')
args = parser.parse_args()


def main():
    app.config['BASIC_AUTH_USERNAME'] = args.username
    app.config['BASIC_AUTH_PASSWORD'] = args.password
    app.run(host='0.0.0.0')
    return


if __name__ == '__main__':
    main()
