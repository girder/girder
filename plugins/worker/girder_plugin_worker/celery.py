import celery

from girder.models.setting import Setting

from .constants import PluginSettings

_celeryapp = None


def getCeleryApp():
    """
    Lazy loader for the celery app. Reloads anytime the settings are updated.
    """
    global _celeryapp

    if _celeryapp is None:
        backend = Setting().get(PluginSettings.BACKEND) or 'rpc://guest:guest@localhost/'
        broker = Setting().get(PluginSettings.BROKER) or 'amqp://guest:guest@localhost/'
        _celeryapp = celery.Celery('girder_worker', backend=backend, broker=broker)
    return _celeryapp
