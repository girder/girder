import filecmp
import os
import pprint

from slicer_cli_web import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    pprint.pprint(vars(args))
    if not filecmp.cmp(args.file1, args.image1):
        print('File and image do not match')
    # args.item1 is a directory if a multi-file item is given; it is a file if
    # it is a single-file item.
    elif os.path.isdir(args.item1) or not filecmp.cmp(args.file1, args.item1):
        print('File and item do not match')
    else:
        print('File, image, and item match')


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
