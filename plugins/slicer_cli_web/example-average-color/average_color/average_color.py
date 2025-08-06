import json
import pprint

import large_image
import numpy
from ctk_cli import CLIArgumentParser  # noqa I004

# imported for side effects - prevents spurious warnings
from slicer_cli_web import ctk_cli_adjustment  # noqa


def main(args):
    print('>> parsed arguments')
    pprint.pprint(vars(args))

    ts = large_image.open(args.imageFile)

    tileMeans = []
    tileWeights = []
    # iterate through the tiles at a particular magnification:
    for tile in ts.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            scale=dict(magnification=5),
            tile_size=dict(width=2048)):
        # The tile image data is in tile['tile'] and is a numpy
        # multi-dimensional array
        mean = numpy.mean(tile['tile'], axis=(0, 1))
        tileMeans.append(mean)
        tileWeights.append(tile['width'] * tile['height'])
        print('x: %d  y: %d  w: %d  h: %d  mag: %g  color: %s' % (
            tile['x'], tile['y'], tile['width'], tile['height'],
            tile['magnification'], ' '.join(f'{val:g}' for val in mean)))
    mean = numpy.average(tileMeans, axis=0, weights=tileWeights)

    channels = ['red', 'green', 'blue']
    if args.channel in channels:
        average = mean[channels.index(args.channel)]
    else:
        average = float(numpy.average(mean))

    print('Average: %g' % average)
    sampleMetadata = {
        'Average Color': average,
        'Average Color By Band': [float(val) for val in mean],
    }
    open(args.outputItemMetadata, 'w').write(json.dumps(sampleMetadata))

    if args.returnParameterFile:
        with open(args.returnParameterFile, 'w') as f:
            f.write('average = %s\n' % average)


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
