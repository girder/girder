# import json
import pprint

import girder_client
# import large_image
# import numpy
from ctk_cli import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    pprint.pprint(vars(args))
    gc = girder_client.GirderClient(apiUrl=args.girderApiUrl)
    gc.setToken(args.girderToken)

    annotations = gc.get('annotation', parameters=dict(limit=100, offset=0, itemId=args.imageId))
    pprint.pprint(annotations)


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
