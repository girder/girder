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
import six
import sourcemap
import sys
import time

import xml.etree.cElementTree as ET


def reset(args):
    """
    This simply deletes all of the intermediate coverage result files in the
    specified directory.
    """
    files = glob.glob(os.path.join(args.coverage_dir, '*.cvg'))
    for file in files:
        os.remove(file)


def _handleFile(line, combined, remappers, args):
    currentPath = line[1:].strip()
    if currentPath not in remappers:
        sourceMapPath = os.path.join(args.source, currentPath) + '.map'
        if os.path.isfile(sourceMapPath):
            remappers[currentPath] = sourcemap.load(open(sourceMapPath))
        else:
            remappers[currentPath] = None
    currentRemapper = remappers[currentPath]
    skip = args.skipCore and currentPath.startswith('clients')

    return currentPath, currentRemapper, skip


def _handleLine(line, combined, currentPath, currentRemapper):
    lineNum, hit = line[1:].split()
    if hit != 'undefined':
        lineNum = int(lineNum)
        hit = int(hit)
        if currentRemapper is not None:
            try:
                # blanket coverage has no column number, so we pass 0
                # unfortunately sourcemap.lookup is throwing if it fails to find
                # a column good enough (even though it has the line that is of
                # interest to us), so we are missing coverage
                token = currentRemapper.lookup(line=lineNum, column=0)
                if token.src is not None and token.src_line > 0:
                    # This could be optimized by caching the result of replace/slice
                    sourcePath = token.src.replace('webpack:///./', '')
                    queryStringPos = sourcePath.find('?')
                    if queryStringPos != -1:
                        sourcePath = sourcePath[:queryStringPos]
                    src_filename, src_extension = os.path.splitext(sourcePath)
                    if src_extension == '.js':
                        combined[sourcePath][token.src_line] |= bool(hit)
                # else:
                #     print "NO MAPPING for " + currentPath + ":" + str(lineNum)
            except IndexError:
                # print "NO MAPPING for " + currentPath + ":" + str(lineNum)
                pass
        else:
            combined[currentPath][lineNum] |= bool(hit)


def combine_report(args):
    """
    Combine all of the intermediate coverage files from each js test, and then
    report them into the desired output format(s).
    """
    if not os.path.exists(args.coverage_dir):
        raise Exception('Coverage directory %s does not exist.' %
                        args.coverage_dir)

    # Step 1: Read and combine intermediate reports
    combined = collections.defaultdict(lambda: collections.defaultdict(int))
    remappers = collections.defaultdict()
    currentPath = None
    currentRemapper = None
    files = glob.glob(os.path.join(args.coverage_dir, '*.cvg'))

    for file in files:
        skip = False
        with open(file) as f:
            for line in f:
                if line[0] == 'F':
                    currentPath, currentRemapper, skip = _handleFile(
                        line, combined, remappers, args)
                elif not skip and line[0] == 'L':
                    _handleLine(line, combined, currentPath, currentRemapper)

    # Step 2: Calculate final aggregate and per-file coverage statistics
    stats = {
        'totalSloc': 0,
        'totalHits': 0,
        'files': {}
    }
    for file, lines in six.viewitems(combined):
        hits, sloc = 0, 0
        for lineNum, hit in six.viewitems(lines):
            sloc += 1
            hits += hit

        stats['totalSloc'] += sloc
        stats['totalHits'] += hits
        stats['files'][file] = {
            'sloc': sloc,
            'hits': hits
        }

    # Step 3: Generate the report
    report(args, combined, stats)


def safe_divide(numerator, denominator):
    """
    Return numerator / denominator or 0 if denominator <= 0.
    """
    numerator = float(numerator)
    denominator = float(denominator)
    if denominator > 0:
        return numerator / denominator
    else:
        return 0


def report(args, combined, stats):
    """
    Generate a cobertura-compliant XML coverage report in the current working
    directory.
    """
    percent = safe_divide(stats['totalHits'], stats['totalSloc']) * 100
    print('Overall total: %s / %s (%.2f%%)' % (
        stats['totalHits'], stats['totalSloc'], percent))

    coverageEl = ET.Element('coverage', {
        'branch-rate': '0',
        'line-rate': str(percent / 100),
        'version': '3.6',
        'timestamp': str(int(time.time()))
    })
    packagesEl = ET.SubElement(coverageEl, 'packages')
    packageEl = ET.SubElement(packagesEl, 'package', {
        'branch-rate': '0',
        'complexity': '0',
        'line-rate': str(percent / 100),
        'name': ''
    })
    classesEl = ET.SubElement(packageEl, 'classes')

    for file, data in six.viewitems(combined):
        lineRate = safe_divide(stats['files'][file]['hits'],
                               stats['files'][file]['sloc'])
        classEl = ET.SubElement(classesEl, 'class', {
            'branch-rate': '0',
            'complexity': '0',
            'line-rate': str(lineRate),
            'filename': file,
            'name': file
        })
        linesEl = ET.SubElement(classEl, 'lines')
        ET.SubElement(classEl, 'methods')
        for lineNum, hit in six.viewitems(data):
            ET.SubElement(linesEl, 'line', {
                'number': str(lineNum),
                'hits': str(hit)
            })

    tree = ET.ElementTree(coverageEl)
    tree.write('js_coverage.xml')

    # If we *actually* covered code, and the percentage is below our threshold, fail
    if len(stats['files']) > 0 and percent < args.threshold:
        print('FAIL: Coverage below threshold (%s%%)' % args.threshold)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--threshold', type=int, help='The minimum required '
                        'coverage level, as a percent.', default=0)
    parser.add_argument('--source', help='The root directory of the source '
                        'repository')
    parser.add_argument(
        '--include-core', dest='skipCore', help='Include core JS files in '
        'the coverage calculations', action='store_false')
    parser.add_argument(
        '--skip-core', dest='skipCore', help='Skip core JS files in the '
        'coverage calculations', action='store_true')
    parser.set_defaults(skipCore=True)
    parser.add_argument('task', help='The task to perform.',
                        choices=['reset', 'combine_report',
                                 'combine_report_skip'])
    parser.add_argument('coverage_dir', help='The directory containing the '
                        'intermediate coverage files.')

    args = parser.parse_args()

    if args.task == 'reset':
        reset(args)
    elif args.task == 'combine_report':
        combine_report(args)
