import itertools
from unittest import mock
import os
import pytest

from girder_worker.docker.io import (
    ChunkedTransferEncodingStreamWriter,
    FDReadStreamConnector,
    FDWriteStreamConnector,
    FileDescriptorReader,
    FileDescriptorWriter,
    NamedPipe,
    NamedPipeReader,
    NamedPipeWriter,
    StdStreamWriter
)

from girder_worker.docker.io.girder import GirderFileStreamReader
from girder_client import GirderClient
from http import client as httplib


def test_FDWriteStreamConnector_fileno_same_as_output_fileno(istream, ostream):
    fd = FDWriteStreamConnector(istream, ostream)
    assert fd.fileno() == ostream.fileno()


def test_FDReadStreamConnector_fileno_same_as_input_fileno(istream, ostream):
    fd = FDReadStreamConnector(istream, ostream)
    assert fd.fileno() == istream.fileno()


def test_FDWriteStreamConnector_write_istream_data_to_ostream(istream, ostream):
    istream.data = b'Test Data'
    FDWriteStreamConnector(istream, ostream).write()
    assert ostream.data == b'Test Data'


def test_FDWriteStreamConnector_open_calls_ostream_open(istream, ostream):
    with mock.patch.object(ostream, 'open', create=True) as ostream_open:
        FDWriteStreamConnector(istream, ostream).open()
        ostream_open.assert_called_once()


def test_FDWriteStreamConnector_close_on_no_istream_data(istream, ostream):
    istream.data = b''
    with mock.patch.object(ostream, 'close') as ostream_close:
        with mock.patch.object(istream, 'close') as istream_close:
            assert FDWriteStreamConnector(istream, ostream).write() == 0
            ostream_close.assert_called_once()
            istream_close.assert_called_once()

    assert ostream.data == b''


def test_FDReadStreamConnector_read_istream_data_to_ostream(istream, ostream):
    istream.data = b'Test Data'
    FDReadStreamConnector(istream, ostream).read()
    assert ostream.data == b'Test Data'


def test_FDReadStreamConnector_open_calls_istream_open(istream, ostream):
    with mock.patch.object(istream, 'open', create=True) as istream_open:
        FDReadStreamConnector(istream, ostream).open()
        istream_open.assert_called_once()


def test_FDReadStreamConnector_close_on_no_istream_data(istream, ostream):
    istream.data = b''
    with mock.patch.object(ostream, 'close') as ostream_close:
        with mock.patch.object(istream, 'close') as istream_close:
            assert FDReadStreamConnector(istream, ostream).read() == 0
            ostream_close.assert_called_once()
            istream_close.assert_called_once()

    assert ostream.data == b''


def test_FileDescriptorReader_calls_os_read():
    with mock.patch('girder_worker.docker.io.os.read') as m:
        fd = FileDescriptorReader(-1)
        fd.read(65536)
        m.assert_called_once_with(-1, 65536)


def test_FileDescriptorReader_calls_os_close():
    fd = FileDescriptorReader(-1)
    with mock.patch('girder_worker.docker.io.os.close') as m:
        fd.close()
        m.assert_called_once_with(-1)


def test_FileDescriptorWriter_calls_os_write():
    with mock.patch('girder_worker.docker.io.os.write') as m:
        fd = FileDescriptorWriter(-1)
        fd.write(65536)
        m.assert_called_once_with(-1, 65536)


def test_FileDescriptorWriter_calls_os_close():
    fd = FileDescriptorWriter(-2)
    with mock.patch('girder_worker.docker.io.os.close') as m:
        fd.close()
        m.assert_called_once_with(-2)


def test_StdStreamWriter_write_writes_to_stream(stream):
    StdStreamWriter(stream).write(b'Test Data')
    assert stream.data == b'Test Data'


def test_StdStreamWriter_close_calls_flush(stream):
    with mock.patch.object(stream, 'flush', create=True) as m:
        StdStreamWriter(stream).close()
        m.assert_called_once()


def test_StdStreamWriter_close_does_not_call_close(stream):
    with mock.patch.object(stream, 'close', create=True) as m:
        StdStreamWriter(stream).close()
        m.assert_not_called()


def test_NamedPipe_makes_a_fifo():
    path = '/tmp/foo.fifo'
    with mock.patch('girder_worker.docker.io.os.mkfifo') as m:
        NamedPipe(path)
        m.assert_called_once_with(path)


def test_NamedPipe_throws_exception_for_missing_fifo_path(tmpdir):
    path = str(tmpdir.join('named_pipe.fifo'))

    np = NamedPipe(path)

    # Remove the FIFO
    os.remove(path)

    with pytest.raises(Exception):  # noqa: B017
        np.open('FLAGS')


def test_NamedPipe_throws_exception_for_non_fifo_path(tmpdir):
    path = str(tmpdir.join('named_pipe.fifo'))

    np = NamedPipe(path)

    # Remove the FIFO
    os.remove(path)

    # Create a regular File
    with open(path, 'w') as fh:
        fh.write('Test Data')

    with pytest.raises(Exception):  # noqa: B017
        np.open('FLAGS')


def test_NamedPipe_throws_exception_for_non_readable_path(tmpdir):
    path = str(tmpdir.join('named_pipe.fifo'))

    np = NamedPipe(path)

    # permissions: --w--w----
    os.chmod(path, 0o220)

    with pytest.raises(Exception):  # noqa: B017
        np.open(os.O_RDONLY)


def test_NamedPipe_open_calls_os_open_on_path(tmpdir):
    path = str(tmpdir.join('named_pipe.fifo'))
    np = NamedPipe(path)

    with mock.patch('girder_worker.docker.io.os.open') as m:
        np.open('FLAGS')
        m.assert_called_once_with(path, 'FLAGS')


def test_NamedPipeReader_open_calls_pipe_open(stream):
    with mock.patch.object(stream, 'open', create=True) as m:
        NamedPipeReader(stream).open()
        m.assert_called_once()


def test_NamedPipeReader_path_is_container_path(stream):
    path = '/some/test/path/'
    npr = NamedPipeReader(stream, container_path=path)
    assert npr.path() == path


def test_NamedPipeReader_fileno_is_pipe_fileno(stream):
    npr = NamedPipeReader(stream)
    assert npr.fileno() == stream.fileno()


def test_NamedPipeWriter_open_calls_pipe_open(stream):
    with mock.patch.object(stream, 'open', create=True) as m:
        NamedPipeWriter(stream).open()
        m.assert_called_once()


def test_NamedPipeWriter_path_is_container_path(stream):
    path = '/some/test/path/'
    npr = NamedPipeWriter(stream, container_path=path)
    assert npr.path() == path


def test_NamedPipeWriter_fileno_is_pipe_fileno(stream):
    npr = NamedPipeWriter(stream)
    assert npr.fileno() == stream.fileno()


def test_ChunkedTransferEncodingStreamWriter_https_creates_ssl_context():
    with mock.patch('girder_worker.docker.io.httplib.HTTPSConnection', autospec=True):
        with mock.patch('girder_worker.docker.io.ssl') as mock_ssl:
            ChunkedTransferEncodingStreamWriter('https://bogus.url.com/')
            mock_ssl.create_default_context.assert_called_once()


def test_ChunkedTransferEncodingStreamWriter_transfer_encoding_in_headers():
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        s.conn.putheader.assert_called_with('Transfer-Encoding', 'chunked')


def test_ChunkedTransferEncodingStreamWriter_custom_headers():
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/', headers={
            'Key1': 'Value1', 'Key2': 'Value2'})
        s.conn.putheader.assert_any_call('Key1', 'Value1')
        s.conn.putheader.assert_any_call('Key2', 'Value2')


def test_ChunkedTransferEncodingStreamWriter_write_sends_newline_separated_length_and_data():
    data = b'BOGUS DATA'
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        s.write(data)
        s.conn.send.assert_has_calls([
            mock.call(hex(len(data))[2:].encode('utf-8')),
            mock.call(b'\r\n'),
            mock.call(data),
            mock.call(b'\r\n')
        ])


def test_ChunkedTransferEncodingStreamWriter_write_on_exception_still_closes():
    data = b'BOGUS DATA'
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        s.conn.send.side_effect = httplib.HTTPException('Bogus Exception')
        with pytest.raises(httplib.HTTPException):
            s.write(data)
            s.conn.close.assert_called_once()
            assert s._closed is True


def test_ChunkedTransferEncodingStreamWriter_close_returns_if_already_closed():
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        s._closed = True
        s.close()
        # Nothing was sent
        s.conn.send.assert_not_called()


def test_ChunkedTransferEncodingStreamWriter_close_sends_empty_message():
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        with mock.patch.object(s.conn, 'getresponse', return_value=mock.MagicMock(status=200)):
            s.close()
            s.conn.send.assert_called_once_with(b'0\r\n\r\n')
            s.conn.close.assert_called_once()


@pytest.mark.parametrize('ec', [301, 302, 404, 405, 500])
def test_ChunkedTransferEncodingStreamWriter_close_raises_exceptions_on_bad_http_codes(ec):
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        s = ChunkedTransferEncodingStreamWriter('http://bogus.url.com/')
        with mock.patch.object(s.conn, 'getresponse', return_value=mock.MagicMock(status=ec)):
            with pytest.raises(Exception):  # noqa: B017
                s.close()
                s.conn.close.assert_called_once()


def test_GirderFileStreamReader_calls_girder_client_downloadFileAsIterator():
    mock_gc = mock.MagicMock(spec=GirderClient)

    # Note: this is only nessisary until 2eb72df is released in girder-client
    mock_gc.downloadFileAsIterator = mock.MagicMock()

    mock_gc.downloadFileAsIterator.return_value = itertools.chain([b'1', b'2', b'3'])

    gfsr = GirderFileStreamReader(mock_gc, -1)
    gfsr.read(65536)
    mock_gc.downloadFileAsIterator.assert_any_call(-1, 65536)


def test_GirderFileStreamReader_returns_bytes_on_stop_iteration():
    mock_gc = mock.MagicMock(spec=GirderClient)

    # Note: this is only nessisary until 2eb72df is released in girder-client
    mock_gc.downloadFileAsIterator = mock.MagicMock()

    mock_gc.downloadFileAsIterator.return_value = itertools.chain([])

    gfsr = GirderFileStreamReader(mock_gc, -1)
    for b in gfsr.read(65536):
        assert type(b, bytes)
