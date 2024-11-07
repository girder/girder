import unittest

from unittest import mock

from girder_worker.utils import is_revoked


class TestCancellation(unittest.TestCase):

    @mock.patch('girder_worker.utils._worker_inspector')
    def test_is_revoked(self, _worker_inspector):
        task = mock.MagicMock()
        task.request.parent_id = None
        task.request.id = '123'
        task.request.hostname = 'hard@worker'

        worker_inspector = mock.MagicMock()
        _worker_inspector.return_value = worker_inspector
        worker_inspector.revoked.return_value = {
            task.request.hostname: [task.request.id]
        }

        # Revoked
        self.assertTrue(is_revoked(task))

        # Not revoked
        task.request.id = '456'
        self.assertFalse(is_revoked(task))
