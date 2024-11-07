import io
import pytest
import random


@pytest.fixture
def stream():
    class MockFileStream(io.BytesIO):
        def __init__(self, fd, *args, **kwargs):
            self._fd = fd
            super().__init__(*args, **kwargs)

        def fileno(self):
            return self._fd

        @property
        def data(self):
            return self.getvalue()

        @data.setter
        def data(self, data):
            self.truncate()
            self.write(data)
            self.seek(0)
    return MockFileStream(random.randrange(4, 100))


istream = stream
ostream = stream
