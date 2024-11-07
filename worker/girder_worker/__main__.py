import sys

from .app import app


def main():
    app.worker_main(argv=['worker'] + sys.argv[1:] if 'worker' not in sys.argv else sys.argv)


if __name__ == '__main__':
    main()
