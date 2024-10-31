import logging
from pathlib import Path

from girder import events
from girder.constants import AccessType
from girder.plugin import getPlugin, GirderPlugin, registerPluginStaticContent
from girder_jobs.models.job import Job

from .api.worker import Worker
from . import event_handlers

logger = logging.getLogger(__name__)


class WorkerPlugin(GirderPlugin):
    DISPLAY_NAME = 'Worker'

    def load(self, info):
        getPlugin('jobs').load(info)

        info['apiRoot'].worker = Worker()

        registerPluginStaticContent(
            plugin='worker',
            js=['/girder-plugin-worker.umd.cjs'],
            css=['/style.css'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )

        events.bind('jobs.schedule', 'worker', event_handlers.schedule)
        events.bind('jobs.status.validate', 'worker', event_handlers.validateJobStatus)
        events.bind('jobs.status.validTransitions', 'worker', event_handlers.validTransitions)
        events.bind('jobs.cancel', 'worker', event_handlers.cancel)
        events.bind('model.job.save.after', 'worker', event_handlers.attachJobInfoSpec)
        events.bind('model.job.save', 'worker', event_handlers.attachParentJob)
        Job().exposeFields(AccessType.SITE_ADMIN, {'celeryTaskId', 'celeryQueue'})
