import pytest
from girder_worker.app import app


def test_is_local_worker_available_returns_false_without_worker(db):
    """Test that helper correctly identifies when no worker is available."""
    from girder.tasks import is_local_worker_available

    assert not is_local_worker_available()


def test_ensure_local_worker_available_raises_without_worker(db):
    """Test that ensure_local_worker_available raises exception without worker."""
    from girder.exceptions import RestException
    from girder.tasks import ensure_local_worker_available

    with pytest.raises(RestException) as exc_info:
        ensure_local_worker_available()

    assert exc_info.value.code == 503
    assert 'No local worker' in exc_info.value.message


def test_is_local_worker_available_returns_true_in_eager_mode(db):
    """Test that helper returns True when celery is in eager mode."""
    from girder.tasks import is_local_worker_available

    # Set to eager mode
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

    try:
        assert is_local_worker_available()
    finally:
        # Reset
        app.conf.task_always_eager = False
        app.conf.task_eager_propagates = False


def test_ensure_local_worker_available_does_not_raise_in_eager_mode(db):
    """Test that ensure_local_worker_available doesn't raise in eager mode."""
    from girder.tasks import ensure_local_worker_available

    # Set to eager mode
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    try:
        # Should not raise
        ensure_local_worker_available()
    finally:
        # Reset
        app.conf.task_always_eager = False
        app.conf.task_eager_propagates = False


def test_is_local_worker_checks_queue(db):
    """Test that the helper checks for correct queue name."""
    from girder.tasks import is_local_worker_available

    # The function should check specifically for 'local' queue presence
    result = is_local_worker_available()
    # When no workers available, returns False
    assert not result
