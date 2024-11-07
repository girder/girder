import unittest
from girder_worker.docker.stream_adapter import DockerStreamPushAdapter


class CaptureAdapter:
    def __init__(self):
        self._captured = b''

    def write(self, data):
        self._captured += data

    def captured(self):
        return self._captured


class TestDemultiplexerPushAdapter(unittest.TestCase):
    def testSinglePayload(self):
        data = [
            b'\x02\x00\x00\x00\x00\x00\x00\x14this is stderr data\n'
        ]

        capture = CaptureAdapter()
        adapter = DockerStreamPushAdapter(capture)
        for d in data:
            adapter.write(d)

        self.assertEqual(capture.captured(), b'this is stderr data\n')

    def testAdapterBrokenUp(self):
        data = [
            b'\x02\x00\x00\x00', b'\x00\x00', b'\x00\x14', b'this is stderr data\n'
        ]

        capture = CaptureAdapter()
        adapter = DockerStreamPushAdapter(capture)
        for d in data:
            adapter.write(d)

        self.assertEqual(capture.captured(), b'this is stderr data\n')

    def testMultiplePayload(self):
        data = [
            b'\x02\x00\x00\x00\x00\x00\x00\x14this is stderr data\n',
            b'\x01\x00\x00\x00\x00\x00\x00\x14this is stdout data\n',
            b'\x01\x00\x00\x00\x00\x00\x00\x0chello world!'
        ]

        capture = CaptureAdapter()
        adapter = DockerStreamPushAdapter(capture)
        for d in data:
            adapter.write(d)

        self.assertEqual(capture.captured(),
                         b'this is stderr data\nthis is stdout data\nhello world!')

    def testMultiplePayloadOneRead(self):
        data = [
            b'\x02\x00\x00\x00\x00\x00\x00\x14this is stderr data\n'
            + b'\x01\x00\x00\x00\x00\x00\x00\x14this is stdout data\n'
            + b'\x01\x00\x00\x00\x00\x00\x00\x0chello world!'
        ]

        capture = CaptureAdapter()
        adapter = DockerStreamPushAdapter(capture)
        for d in data:
            adapter.write(d)

        self.assertEqual(capture.captured(),
                         b'this is stderr data\nthis is stdout data\nhello world!')
