import sys

from girder_worker_utils.tee import Tee, tee_stdout, TeeStdErr, TeeStdOut


@tee_stdout
class TeeCapture(Tee):
    def __init__(self, *args, **kwargs):
        self.buf = ''
        super().__init__(*args, **kwargs)

    def write(self, message, **kwargs):
        self.buf += message
        super().write(message, **kwargs)


def test_tee_sys_write_stdout(capfd):
    with TeeStdOut():
        sys.stdout.write('Test String')
        sys.stdout.flush()

    out, err = capfd.readouterr()
    assert out == 'Test String'


def test_tee_print_stdout(capfd):
    with TeeStdOut():
        print('Test String')

    out, err = capfd.readouterr()
    assert out == 'Test String\n'


def test_tee_stdout_sys_write_pass_through_false(capfd):
    with TeeStdOut(pass_through=False):
        sys.stdout.write('Test String')
        sys.stdout.flush()

    out, err = capfd.readouterr()
    assert out == ''


def test_tee_stdout_print_pass_through_false(capfd):
    with TeeStdOut(pass_through=False):
        print('Test String')

    out, err = capfd.readouterr()
    assert out == ''


def test_tee_sys_write_stderr(capfd):
    with TeeStdErr():
        sys.stderr.write('Test String')
        sys.stderr.flush()

    out, err = capfd.readouterr()
    assert err == 'Test String'


def test_tee_stderr_sys_write_pass_through_false(capfd):
    with TeeStdErr(pass_through=False):
        sys.stderr.write('Test String')
        sys.stderr.flush()

    out, err = capfd.readouterr()
    assert err == ''


def test_tee_overwrites_write(capfd):
    with TeeCapture() as o:
        print('Test String')
        assert o.buf == 'Test String\n'

    out, err = capfd.readouterr()
    assert out == 'Test String\n'


def test_tee_overwrites_write_pass_through_false(capfd):
    with TeeCapture(pass_through=False) as o:
        print('Test String')
        assert o.buf == 'Test String\n'

    out, err = capfd.readouterr()
    assert out == ''


def test_tee_reset_function_resets(capfd):
    original_stdout = sys.stdout

    o = TeeCapture()

    print('Test String')
    out, err = capfd.readouterr()

    assert o.buf == 'Test String\n'
    assert out == 'Test String\n'

    o.reset()

    assert sys.stdout == original_stdout


def test_tee_multiple_tee_objects_downstream():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    assert sys.stdout == o3
    assert sys.stdout._downstream == o2
    assert sys.stdout._downstream._downstream == o1
    assert sys.stdout._downstream._downstream._downstream == original_stdout


def test_tee_multiple_tee_objects_each_recieves_write(capfd):
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    assert sys.stdout == o3
    assert o3._downstream == o2
    assert o2._downstream == o1
    assert o1._downstream == original_stdout

    print('Test String')

    assert o3.buf == 'Test String\n'
    assert o2.buf == 'Test String\n'
    assert o1.buf == 'Test String\n'

    out, err = capfd.readouterr()
    assert out == 'Test String\n'


def test_tee_multiple_tee_objects_reset_o1():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    o1.reset()

    assert o3._downstream == o2
    assert o2._downstream == original_stdout


def test_tee_multiple_tee_objects_reset_o2():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    o2.reset()

    assert o3._downstream == o1
    assert o1._downstream == original_stdout


def test_tee_multiple_tee_objects_reset_o3():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    o3.reset()

    assert sys.stdout == o2
    assert o2._downstream == o1
    assert o1._downstream == original_stdout


def test_tee_multiple_tee_objects_reset_o3_then_o1():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    o3.reset()

    assert sys.stdout == o2
    assert o2._downstream == o1
    assert o1._downstream == original_stdout

    o1.reset()

    assert sys.stdout == o2
    assert o2._downstream == original_stdout


def test_tee_multiple_tee_objects_reset_o3_then_o1_then_o2():
    original_stdout = sys.stdout
    o1, o2, o3 = TeeCapture(), TeeCapture(), TeeCapture()

    o3.reset()

    assert sys.stdout == o2
    assert o2._downstream == o1
    assert o1._downstream == original_stdout

    o1.reset()

    assert sys.stdout == o2
    assert o2._downstream == original_stdout

    o2.reset()

    assert sys.stdout == original_stdout
