# -*- coding: utf-8 -*-
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
except ImportError:
    zlib = None

__all__ = ('STORE', 'DEFLATE', 'ZipGenerator')


Z64_LIMIT = (1 << 31) - 1
Z_FILECOUNT_LIMIT = 1 << 16
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
        if os.sep != '/' and os.sep in filename:
            filename = filename.replace(os.sep, '/')
        if isinstance(filename, str):
            filename = filename.encode('utf8')
        # Escaping or locale conversion should go here
        nullByte = filename.find(b'\x00')
        if nullByte >= 0:
            filename = filename[0:nullByte]
        self.filename = filename
        self.timestamp = timestamp
        self.compressType = STORE
        if sys.platform == 'win32':
            self.createSystem = 0
        else:
            self.createSystem = 3
        self.createVersion = 20
        self.extractVersion = 20
        self.externalAttr = 0

    def dataDescriptor(self):
        if self.compressSize > Z64_LIMIT or self.fileSize > Z64_LIMIT:
            fmt = b'<4sLQQ'
        else:
            fmt = b'<4sLLL'
        return struct.pack(
            fmt, b'PK\x07\x08', self.crc, self.compressSize, self.fileSize)

    def fileHeader(self):
        """
        Return the per-file header as a string.
        """
        dt = self.timestamp
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)

        header = struct.pack(
            b'<4s2B4HLLL2H', b'PK\003\004', self.extractVersion, 0, 0x8,
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
            raise RuntimeError('Missing zlib module')

        self.files = []
        self.compression = compression
        self.useCRC = True
        self.rootPath = rootPath
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
        fullpath = os.path.join(self.rootPath, path)
        header = ZipInfo(fullpath, time.localtime()[0:6])
        header.externalAttr = (0o100644 & 0xFFFF) << 16
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
            if isinstance(buf, str):
                buf = buf.encode('utf8')
            fileSize += len(buf)
            if self.useCRC:
                crc = binascii.crc32(buf, crc) & 0xFFFFFFFF
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
                headerOffset = 0xffffffff
            else:
                headerOffset = header.headerOffset

            if extra:
                extraData = struct.pack(
                    b'<hh' + b'q' * len(extra), 1, 8 * len(extra), *extra)
                extractVersion = max(45, header.extractVersion)
                createVersion = max(45, header.createVersion)
            else:
                extraData = b''
                extractVersion = header.extractVersion
                createVersion = header.createVersion

            centdir = struct.pack(
                b'<4s4B4HLLL5HLL', b'PK\001\002', createVersion,
                header.createSystem, extractVersion, 0, 0x8,
                header.compressType, dostime, dosdate, header.crc, compressSize,
                fileSize, len(header.filename), len(extraData), 0, 0, 0,
                header.externalAttr, headerOffset)

            data.append(self._advanceOffset(centdir))
            data.append(self._advanceOffset(header.filename))
            data.append(self._advanceOffset(extraData))

        pos2 = self.offset
        offsetVal = pos1
        size = pos2 - pos1

        if pos1 > Z64_LIMIT or size > Z64_LIMIT or count >= Z_FILECOUNT_LIMIT:
            zip64endrec = struct.pack(
                b'<4sqhhLLqqqq', b'PK\x06\x06', 44, 45, 45, 0, 0, count, count,
                size, pos1)
            data.append(self._advanceOffset(zip64endrec))

            zip64locrec = struct.pack(b'<4sLqL', b'PK\x06\x07', 0, pos2, 1)
            data.append(self._advanceOffset(zip64locrec))

            count = min(count, 0xFFFF)
            size = min(size, 0xFFFFFFFF)
            offsetVal = min(offsetVal, 0xFFFFFFFF)

        endrec = struct.pack(b'<4s4H2LH', b'PK\005\006', 0, 0, count, count,
                             size, offsetVal, 0)
        data.append(self._advanceOffset(endrec))

        return b''.join(data)
