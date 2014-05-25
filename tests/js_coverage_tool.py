#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

"""
This module is used for managing javascript coverage data output by the tests
running in the phantom environment. It is used to reset the coverage, as well
as to combine and report it once all of the tests have been run.
"""

import argparse
import glob
import os


def reset(args):
    """
    This simply deletes all of the intermediate coverage result files in the
    specified directory.
    """
    files = glob.glob(os.path.join(args.coverage_dir, '*.cvg'))
    for file in files:
        os.remove(file)


def combine_report(args):
    """
    Combine all of the intermediate coverage files from each js test, and then
    report them into the desired output format(s).
    """
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--threshold', type=int, help='The minimum required '
                        'coverage level, as a percent.', default=0)
    parser.add_argument('--source', help='The root directory of the source '
                        'repository')
    parser.add_argument('task', help='The task to perform.',
                        choices=['reset', 'combine_report'])
    parser.add_argument('coverage_dir', help='The directory containing the '
                        'intermediate coverage files.')

    args = parser.parse_args()

    if not os.path.exists(args.coverage_dir):
        raise Exception('Coverage directory {} does not exist.'.format(
            args.coverage_dir))

    if args.task == 'reset':
        reset(args)
    elif args.task == 'combine_report':
        combine_report(args)
