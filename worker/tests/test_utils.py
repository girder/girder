import sys
from girder_worker.utils import TeeStdOutCustomWrite


def test_TeeStdOutCustomWrite(capfd):
    nonlocal_ = {'data': ''}

    def _append_to_data(message, **kwargs):
        nonlocal_['data'] += message

    with TeeStdOutCustomWrite(_append_to_data):
        sys.stdout.write('Test String')
        sys.stdout.flush()

    assert nonlocal_['data'] == 'Test String'

    out, err = capfd.readouterr()
    assert out == 'Test String'
