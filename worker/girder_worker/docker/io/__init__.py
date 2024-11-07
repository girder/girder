import os
import errno
import stat
import abc
import urllib
import ssl
import sys
from http import client as httplib


class FDStreamConnector(metaclass=abc.ABCMeta):
    """
    FDStreamConnector is an abstract base class used to connect a read(input) and write(output)
    stream.
    """

    def __init__(self, input, output):
        self.input = input
        self.output = output

    @abc.abstractmethod
    def open(self):
        """
        Open the stream connector, delegated to implementation.
        """

    @abc.abstractmethod
    def close(self):
        """
        Close the stream connector, delegated to implementation.
        """

    @abc.abstractmethod
    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns: The file descriptor that should be used to determine if the connector
                 has data to process.
        """


class FDWriteStreamConnector(FDStreamConnector):
    """
    FDWriteStreamConnector can be used to connect a read and write stream. The write
    side of the connection will be used in the select loop to trigger write i.e
    the file descriptor from the write stream will be used in the select call.

    This is typically used to stream data to a named pipe that will be read inside
    a container.
    """

    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns: The file descriptor for write(output) side of the connection.
        """
        return self.output.fileno()

    def write(self, n=65536):
        """
        Called when it is detected the output side of this connector is ready
        to write. Reads (potentially blocks) at most n bytes and writes them to
        the output ends of this connector. If no bytes could be read, the connector
        is closed.

        :param n The maximum number of bytes to write.
        :type n int
        :returns: The actual number of bytes written.
        """
        buf = self.input.read(n)

        if buf:
            return self.output.write(buf)
        else:
            self.close()

        return 0

    def open(self):
        """
        Calls open on the output side of this connector.
        """
        self.output.open()

    def close(self):
        """
        Closes the output side of this connector, followed by the input side.
        """
        self.output.close()
        if hasattr(self.input, 'close'):
            self.input.close()


class FDReadStreamConnector(FDStreamConnector):
    """
    FDReadStreamConnector can be used to connect a read and write stream. The read
    side of the connection will be used in the select loop to trigger write i.e
    the file descriptor from the read stream will be used in the select call.

    This is typically used to stream data from a named pipe that is being written
    to inside a container.
    """

    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns: The file descriptor for read(input) side of the connection.
        """
        return self.input.fileno()

    def read(self, n=65536):
        """
        Called when it is detected the input side of this connector is ready
        to read. Reads at most n bytes and writes them to the output ends of
        this connector. If no bytes could be read, the connector is closed.

        :param n The maximum number of bytes to read.
        :type n int
        :returns: The actual number of bytes read.
        """
        buf = self.input.read(n)

        if buf:
            self.output.write(buf)
            # TODO PushAdapter/Writers should return number of bytes actually
            # written.
            return len(buf)
        else:
            self.close()

        return 0

    def open(self):
        """
        Calls open on the input side of this connector.
        """
        self.input.open()

    def close(self):
        """
        Closes the output side of this connector, followed by the input side.
        """
        self.input.close()
        self.output.close()


class StreamReader(metaclass=abc.ABCMeta):
    """
    This represents the interface that must be implemented by a stream reader.
    """

    @abc.abstractmethod
    def read(self, buf_len):
        """
        Stream readers must implement this method, which is responsible for
        reading up to ``buf_len`` bytes from the stream. For now, this is
        expected to be a blocking read, and should return an empty string to
        indicate the end of the stream.
        """

    def close(self):
        """
        Close the input stream. Called after the last data is read.
        """
        pass


class StreamWriter(metaclass=abc.ABCMeta):
    """
    This represents the interface that must be implemented by a stream writer.
    """

    @abc.abstractmethod
    def write(self, buf):
        """
        Write a chunk of data to the output stream.
        """

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        pass


class FileDescriptorReader(StreamReader):
    """
    Reader to read from a file descriptor.
    """

    def __init__(self, fd):
        self._fd = fd

    def fileno(self):
        return self._fd

    def read(self, n):
        return os.read(self.fileno(), n)

    def close(self):
        os.close(self.fileno())


class FileDescriptorWriter(StreamWriter):
    """
    Writer to write to a file descriptor.
    """

    def __init__(self, fd):
        self._fd = fd

    def fileno(self):
        return self._fd

    def write(self, buf):
        return os.write(self.fileno(), buf)

    def close(self):
        os.close(self.fileno())


class StdStreamWriter(StreamWriter):
    """
    Writer for write to stdout and stderr.
    """

    def __init__(self, stream):
        self._stream = stream

    def write(self, buf):
        return self._stream.write(buf)

    def close(self):
        # Don't close std streams!
        self._stream.flush()


class NamedPipe:
    """
    A named pipe.
    """

    def __init__(self, path):
        self.path = path
        self._fd = None
        os.mkfifo(self.path)

    def open(self, flags):

        if self._fd is None:
            if not os.path.exists(self.path):
                raise Exception('Input pipe does not exist: %s' % self._path)
            if not stat.S_ISFIFO(os.stat(self.path).st_mode):
                raise Exception('Input pipe must be a fifo object: %s' % self._path)

            try:
                self._fd = os.open(self.path, flags)
            except OSError as e:
                if e.errno != errno.ENXIO:
                    raise e

    def fileno(self):
        return self._fd


class NamedPipeReader(FileDescriptorReader):
    """
    Reader to read from a named pipe.
    """

    def __init__(self, pipe, container_path=None):
        super().__init__(None)
        self._pipe = pipe
        self._container_path = container_path

    def open(self):
        self._pipe.open(os.O_RDONLY | os.O_NONBLOCK)

    def path(self):
        """
        The argument to pass to the docker container's entrypoint. In this case
        the path to the named pipe.
        """
        return self._container_path

    def fileno(self):
        return self._pipe.fileno()


class NamedPipeWriter(FileDescriptorWriter):
    """
    Write to write to a named pipe.
    """

    def __init__(self, pipe, container_path=None):
        super().__init__(None)
        self._pipe = pipe
        self._container_path = container_path

    def open(self):
        self._pipe.open(os.O_WRONLY | os.O_NONBLOCK)

    def path(self):
        """
        The argument to pass to the docker container's entrypoint. In this case
        the path to the named pipe.
        """
        return self._container_path

    def fileno(self):
        return self._pipe.fileno()


class ChunkedTransferEncodingStreamWriter(StreamWriter):
    def __init__(self, url, headers=None):
        self._url = url
        headers = headers or {}

        """
        Uses HTTP chunked transfer-encoding to stream a request body to a
        server. Unfortunately requests does not support hooking into this logic
        easily, so we use the lower-level httplib module.
        """
        self._closed = False

        parts = urllib.parse.urlparse(self._url)
        if parts.scheme == 'https':
            ssl_context = ssl.create_default_context()
            conn = httplib.HTTPSConnection(parts.netloc, context=ssl_context)
        else:
            conn = httplib.HTTPConnection(parts.netloc)

        try:
            url = parts.path
            if parts.query is not None:
                url = '%s?%s' % (url, parts.query)
            conn.putrequest('POST',
                            url, skip_accept_encoding=True)

            for header, value in headers.items():
                conn.putheader(header, value)

            conn.putheader('Transfer-Encoding', 'chunked')

            conn.endheaders()  # This actually flushes the headers to the server
        except Exception:
            sys.stderr.write('HTTP connection to "%s" failed.\n' % self._url)
            conn.close()
            raise

        self.conn = conn

    def write(self, buf):
        """
        Write a chunk of data to the output stream in accordance with the
        chunked transfer encoding protocol.
        """
        try:
            self.conn.send(hex(len(buf))[2:].encode('utf-8'))
            self.conn.send(b'\r\n')
            self.conn.send(buf)
            self.conn.send(b'\r\n')
        except Exception:
            resp = self.conn.getresponse()
            sys.stderr.write(
                'Exception while sending HTTP chunk to %s, status was %s, '
                'message was:\n%s\n' % (self._url, resp.status,
                                        resp.read()))
            self.conn.close()
            self._closed = True
            raise

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        if self._closed:
            return

        try:
            self.conn.send(b'0\r\n\r\n')
            resp = self.conn.getresponse()
            if resp.status >= 300 and resp.status < 400:
                raise Exception('Redirects are not supported for streaming '
                                'requests at this time. %d to Location: %s' % (
                                    resp.status, resp.getheader('Location')))
            if resp.status >= 400:
                raise Exception(
                    'HTTP stream output to %s failed with status %d. Response '
                    'was: %s' % (
                        self.output_spec['url'], resp.status, resp.read()))
        finally:
            self.conn.close()
