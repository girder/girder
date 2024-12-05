import argparse
import os
import sys
import time

from progress_helper import ProgressHelper

if __name__ == '__main__':
    if '--json' in sys.argv:
        json_spec_file = os.path.splitext(sys.argv[0])[0] + '.json'
        with open(json_spec_file) as f:
            print(f.read())
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument('--count', dest='count', type=int, default=10)
    parser.add_argument('--sleep', dest='sleep', type=float, default=1)

    args = parser.parse_args()
    with ProgressHelper('Example', 'Sleeping mostly') as p:
        for i in range(args.count):
            print('Sleeping...')
            if i:
                p.message('Sleeping for %g seconds' % ((args.count - i) * args.sleep))
            p.progress(float(i) / args.count)
            time.sleep(args.sleep)
        p.message('Done')
        p.progress(1)
