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
This module is essentially a subset of the python zipfile module that has been
modified to allow it to read arbitrary streams (using generators) as input,
instead of only accepting files. It also streams the output using generators.

Example of creating and consuming a streaming zip:

    zip = ziputil.ZipGenerator('TopLevelFolder')

    for data in zip.addFile(lambda: 'hello world', 'hello.txt'):
        yield data

    yield zip.footer()
"""

import binascii
import os
import struct
import sys
import time

try:
    import zlib
except ImportError:  # pragma: no cover
    zlib = None

__all__ = ['STORE', 'DEFLATE', 'ZipGenerator']


Z64_LIMIT = (1 << 31) - 1
STORE = 0
DEFLATE = 8


class ZipInfo(object):

    __slots__ = (
        'filename',
        'timestamp',
        'compressType',
        'createSystem',
        'createVersion',
        'extractVersion',
        'externalAttr',
        'headerOffset',
        'crc',
        'compressSize',
        'fileSize'
    )

    def __init__(self, filename, timestamp):
        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        nullByte = filename.find(chr(0))
        if nullByte >= 0:
            filename = filename[0:nullByte]
        if os.sep != '/' and os.sep in filename:
            filename = filename.replace(os.sep, '/')

        self.filename = str(filename)
        self.timestamp = timestamp
        self.compressType = STORE
        if sys.platform == 'win32':
            self.createSystem = 0  # pragma: no cover
        else:
            self.createSystem = 3
        self.createVersion = 20
        self.extractVersion = 20
        self.externalAttr = 0

    def dataDescriptor(self):
        if self.compressSize > Z64_LIMIT or self.fileSize > Z64_LIMIT:
            fmt = '<4slQQ'
        else:
            fmt = '<4slLL'
        return struct.pack(
            fmt, 'PK\x07\x08', self.crc, self.compressSize, self.fileSize)

    def fileHeader(self):
        """
        Return the per-file header as a string.
        """
        dt = self.timestamp
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)

        header = struct.pack(
            '<4s2B4HlLL2H', 'PK\003\004', self.extractVersion, 0, 0x8,
            self.compressType, dostime, dosdate, 0, 0, 0, len(self.filename), 0)
        return header + self.filename


class ZipGenerator(object):
    """
    This class can be used to create a streaming zip file that consumes from
    one generator and writes to another.
    """
    def __init__(self, rootPath='', compression=STORE):
        """
        :param rootPath: The root path for all files within this archive.
        :type rootPath: str
        :param compression: Whether files in this archive should be compressed.

        :type
        """
        if compression == DEFLATE and not zlib:
            raise RuntimeError('Missing zlib module')  # pragma: no cover

        self.files = []
        self.compression = compression
        self.rootPath = str(rootPath)
        self.offset = 0

    def _advanceOffset(self, data):
        """
        Call this whenever data is added to the archive to keep track of the
        offset of the data.
        """
        self.offset += len(data)
        return data

    def addFile(self, generator, path):
        """
        Generates data to add a file at the given path in the archive.
        :param generator: Generator function that will yield the file contents.
        :type generator: function
        :param path: The path within the archive for this entry.
        :type path: str
        """
        header = ZipInfo(os.path.join(self.rootPath, str(path)),
                         time.localtime()[0:6])
        header.externalAttr = (0100644 & 0xFFFF) << 16L
        header.compressType = self.compression
        header.headerOffset = self.offset

        header.crc = crc = 0
        header.compressSize = compressSize = 0
        header.fileSize = fileSize = 0
        yield self._advanceOffset(header.fileHeader())
        if header.compressType == DEFLATE:
            compressor = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                                          zlib.DEFLATED, -15)
        else:
            compressor = None

        for buf in generator():
            if not buf:
                break
            fileSize += len(buf)
            crc = binascii.crc32(buf, crc)
            if compressor:
                buf = compressor.compress(buf)
                compressSize += len(buf)
            yield self._advanceOffset(buf)

        if compressor:
            buf = compressor.flush()
            compressSize += len(buf)
            yield self._advanceOffset(buf)
            header.compressSize = compressSize
        else:
            header.compressSize = fileSize
        header.crc = crc
        header.fileSize = fileSize
        yield self._advanceOffset(header.dataDescriptor())
        self.files.append(header)

    def footer(self):
        """
        Once all zip files have been added with addFile, you must call this
        to get the footer of the archive.
        """
        data = []
        count = 0
        pos1 = self.offset
        for header in self.files:
            count += 1
            dt = header.timestamp
            dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
            dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
            extra = []
            if header.fileSize > Z64_LIMIT or header.compressSize > Z64_LIMIT:
                extra.append(header.fileSize)
                extra.append(header.compressSize)
                fileSize = compressSize = 0xffffffff
            else:
                fileSize = header.fileSize
                compressSize = header.compressSize

            if header.headerOffset > Z64_LIMIT:
                extra.append(header.headerOffset)
                headerOffset = -1
            else:
                headerOffset = header.headerOffset

            if extra:
                extraData = struct.pack(
                    '<hh' + 'q'*len(extra), 1, 8*len(extra), *extra)
                extractVersion = max(45, header.extractVersion)
                createVersion = max(45, header.createVersion)
            else:
                extraData = ''
                extractVersion = header.extractVersion
                createVersion = header.createVersion

            centdir = struct.pack(
                '<4s4B4HlLL5HLl', 'PK\001\002', createVersion,
                header.createSystem, extractVersion, 0, 0x8,
                header.compressType, dostime, dosdate, header.crc, compressSize,
                fileSize, len(header.filename), len(extraData), 0, 0, 0,
                header.externalAttr, headerOffset)

            data.append(self._advanceOffset(centdir))
            data.append(self._advanceOffset(header.filename))
            data.append(self._advanceOffset(extraData))

        pos2 = self.offset
        offsetVal = pos1

        if pos1 > Z64_LIMIT:
            zip64endrec = struct.pack(
                '<4sqhhllqqqq', 'PK\x06\x06', 44, 45, 45, 0, 0, count, count,
                pos2 - pos1, pos1)
            data.append(self._advanceOffset(zip64endrec))

            zip64locrec = struct.pack('<4slql', 'PK\x06\x07', 0, pos2, 1)
            data.append(self._advanceOffset(zip64locrec))

            offsetVal = -1

        endrec = struct.pack('<4s4H2lH', 'PK\005\006', 0, 0, count, count,
                             pos2 - pos1, offsetVal, 0)
        data.append(self._advanceOffset(endrec))

        return ''.join(data)
