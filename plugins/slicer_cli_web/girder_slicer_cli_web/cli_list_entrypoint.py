import argparse
import json
import logging
import os
import subprocess
import sys
import textwrap as _textwrap

logger = logging.getLogger(__name__)


class _MultilineHelpFormatter(argparse.HelpFormatter):
    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        paragraphs = text.split('|n')
        multiline_text = ''
        for paragraph in paragraphs:
            formatted_paragraph = '\n' + _textwrap.fill(
                paragraph, width,
                initial_indent=indent,
                subsequent_indent=indent) + '\n'
            multiline_text += formatted_paragraph
        return multiline_text


def _make_print_cli_list_spec_action(cli_list_spec_file):

    with open(cli_list_spec_file) as f:
        str_cli_list_spec = f.read()

    class _PrintCLIListSpecAction(argparse.Action):

        def __init__(self,
                     option_strings,
                     dest=argparse.SUPPRESS,
                     default=argparse.SUPPRESS,
                     help=None):
            super().__init__(
                option_strings=option_strings,
                dest=dest,
                default=default,
                nargs=0,
                help=help)

        def __call__(self, parser, namespace, values, option_string=None):
            print(str_cli_list_spec)
            parser.exit()

    return _PrintCLIListSpecAction


def CLIListEntrypoint(cli_list_spec_file=None, cwd=None):

    if cli_list_spec_file is None:
        cli_list_spec_file = os.path.join(cwd or os.getcwd(), 'slicer_cli_list.json')

    # Parse CLI List spec
    with open(cli_list_spec_file) as f:
        cli_list_spec = json.load(f)

    # create command-line argument parser
    cmdparser = argparse.ArgumentParser(
        formatter_class=_MultilineHelpFormatter
    )

    # add --cli_list
    cmdparser.add_argument(
        '--list_cli',
        action=_make_print_cli_list_spec_action(cli_list_spec_file),
        help='Prints the json file containing the list of CLIs present'
    )

    # add cl-rel-path argument
    cmdparser.add_argument('cli',
                           help='CLI to run',
                           metavar='<cli>',
                           choices=cli_list_spec.keys())

    args = cmdparser.parse_args(sys.argv[1:2])

    args.cli = os.path.normpath(args.cli)

    if cli_list_spec[args.cli]['type'] == 'python':

        script_file = os.path.join(cwd or os.getcwd(), args.cli,
                                   os.path.basename(args.cli) + '.py')

        # python <cli-rel-path>/<cli-name>.py [<args>]
        output_code = subprocess.call([sys.executable, script_file] + sys.argv[2:])

    elif cli_list_spec[args.cli]['type'] == 'cxx':

        script_file = os.path.join(cwd or os.getcwd(), args.cli, os.path.basename(args.cli))

        if os.path.isfile(script_file):

            # ./<cli-rel-path>/<cli-name> [<args>]
            output_code = subprocess.call([script_file] + sys.argv[2:])

        else:

            # assumes parent dir of CLI executable is in ${PATH}
            output_code = subprocess.call([os.path.basename(args.cli)] + sys.argv[2:])

    else:
        logger.exception('CLIs of type %s are not supported',
                         cli_list_spec[args.cli]['type'])
        raise Exception(
            'CLIs of type %s are not supported',
            cli_list_spec[args.cli]['type']
        )

    return output_code


if __name__ == '__main__':
    sys.exit(CLIListEntrypoint())
