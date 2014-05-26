# Utility script for reading a python config file with ConfigParser and
# converting it to a JSON object for portability

import json
import os
import sys

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.stderr.write("Pass a config file to parse as the first argument.\n")
        sys.exit(1)

    f = sys.argv[1]
    if not os.path.isfile(f):
        sys.stderr.write("File does not exist: {}.\n".format(f))
        sys.exit(1)

    config = ConfigParser()
    config.read(f)

    print(json.dumps({k: dict(config.items(k)) for k in config.sections()}))
