import pprint

from slicer_cli_web import CLIArgumentParser


def main(args):
    if args.stringWithOptions == '__datalist__':
        print(
            '<element>First option</element>\n'
            '<element>Second option</element>\n'
            '<element>Third option</element>\n')
        return
    print('>> parsed arguments')
    print('%r' % args)
    pprint.pprint(vars(args), width=1000)
    with open(args.returnParameterFile, 'w') as f:
        f.write('>> parsed arguments\n')
        f.write('%r\n' % args)
    with open(args.arg1, 'w') as f:
        f.write('example\n')


if __name__ == '__main__':
    parser = CLIArgumentParser()
    main(parser.parse_args())
