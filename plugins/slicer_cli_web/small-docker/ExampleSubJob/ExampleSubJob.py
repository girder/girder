import argparse
import os
import sys

import girder_client

if __name__ == '__main__':
    if '--json' in sys.argv:
        json_spec_file = os.path.splitext(sys.argv[0])[0] + '.json'
        with open(json_spec_file) as f:
            print(f.read())
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument('--count', dest='count', type=int, default=10)
    parser.add_argument('--sleep', dest='sleep', type=float, default=1)
    parser.add_argument('--api-url', dest='girderApiUrl', default='')
    parser.add_argument('--girder-token', dest='girderToken', default='')

    args = parser.parse_args()
    gc = girder_client.GirderClient(apiUrl=args.girderApiUrl)
    gc.token = args.girderToken
    gc.post(
        'slicer_cli_web/girder_slicer_cli_web_small/ExampleProgress/run',
        parameters={
            'Rounds': args.count,
            'Sleep': args.sleep
        })
