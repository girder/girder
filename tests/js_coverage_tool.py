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
import collections
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

    # Step 1: Read and combine intermediate reports
    combined = collections.defaultdict(lambda: collections.defaultdict(int))
    currentSource = None
    files = glob.glob(os.path.join(args.coverage_dir, '*.cvg'))
    for file in files:
        with open(file) as f:
            for line in f:
                if line[0] == 'F':
                    currentSource = combined[line[1:].strip()]
                elif line[0] == 'L':
                    lineNum, hit = [int(x) for x in line[1:].split()]
                    currentSource[lineNum] |= hit

    # Step 2: Calculate aggregate coverage
    aggregate = {
        'totalSloc': 0,
        'totalHits': 0,
        'files': {}
    }
    for file, lines in combined.iteritems():
        hits, sloc = 0, 0
        for lineNum, hit in lines.iteritems():
            sloc += 1
            hits += hit

        aggregate['totalSloc'] += sloc
        aggregate['totalHits'] += hits
        aggregate['files'][file] = {
            'sloc': sloc,
            'hits': hits,
            'lines': lines
        }

    # Step 3: Generate the report
    report(aggregate)


def report(data):
    print data

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
