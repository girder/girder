import struct
import json


class StreamPushAdapter:
    """
    This represents the interface that must be implemented by push adapters for
    IO modes that want to implement streaming output.
    """

    def write(self, buf):
        """
        Write a chunk of data to the output stream.
        """
        raise NotImplementedError

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        pass


class JobProgressAdapter(StreamPushAdapter):
    """
    This reads structured JSON documents one line at a time and sends
    them as progress events via the JobManager.

    :param job_manager: The job manager to use to send the progress events.
    :type job_manager: girder_worker.utils.JobManager
    """

    def __init__(self, job_manager):
        super().__init__()

        self.job_manager = job_manager
        self._buf = b''

    def write(self, buf):
        lines = buf.split(b'\n')
        if self._buf:
            lines[0] = self._buf + lines[0]
        self._buf = lines[-1]

        for line in lines[:-1]:
            self._parse(line)

    def _parse(self, line):
        try:
            doc = json.loads(line.decode('utf8'))
        except ValueError:
            return  # TODO log?

        if not isinstance(doc, dict):
            return  # TODO log?

        self.job_manager.updateProgress(
            total=doc.get('total'), current=doc.get('current'), message=doc.get('message'))


class DockerStreamPushAdapter(StreamPushAdapter):
    """
    An adapter that reads a docker stream. The format is a Header and a Payload (frame)
    where the header has the following format:

    .. code-block:: none

        header := [8]byte{STREAM_TYPE, 0, 0, 0, SIZE1, SIZE2, SIZE3, SIZE4}

    We want to read the header to get the size of the payload, read the payload
    and forward it on to another adapter.
    """

    def __init__(self, adapter):
        self._adapter = adapter
        self._reset()

    def _reset(self):
        self._header = b''
        self._header_bytes_read = 0
        self._payload_bytes_read = 0
        self._payload_size = None

    def _read_header(self):
        """
        Read the header or part of the header. When the head has been read, the
        payload size is decoded and returned, otherwise return None.
        """
        bytes_to_read = min(8 - self._header_bytes_read, self._data_length - self._data_offset)
        self._header += self._data[self._data_offset:self._data_offset + bytes_to_read]
        self._data_offset += bytes_to_read
        self._header_bytes_read += bytes_to_read

        if self._header_bytes_read == 8:
            _, payload_size = struct.unpack('>BxxxL', self._header)

            return payload_size

    def _read_payload(self):
        """
        Read the payload or part of the payload. The data is written directly to
        the wrapped adapter.
        """
        bytes_to_read = min(self._payload_size - self._payload_bytes_read,
                            self._data_length - self._data_offset)
        self._adapter.write(self._data[self._data_offset:self._data_offset + bytes_to_read])
        self._data_offset += bytes_to_read
        self._payload_bytes_read += bytes_to_read

    def write(self, data):
        self._data = data
        self._data_length = len(data)
        self._data_offset = 0

        # While we still have data iterate over it
        while self._data_length > self._data_offset:
            # We are reading the header
            if self._header_bytes_read < 8:
                self._payload_size = self._read_header()

            # We are reading the payload
            if self._payload_size and self._payload_bytes_read < self._payload_size:
                self._read_payload()

            # We are done with this payload
            if self._payload_size == self._payload_bytes_read:
                self._reset()

    def close(self):
        self._adapter.close()
