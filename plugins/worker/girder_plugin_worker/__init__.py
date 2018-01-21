#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder import events
from girder.constants import AccessType
from girder.plugin import getPlugin, GirderPlugin
from girder_plugin_jobs.models.job import Job

from .api.worker import Worker
from . import event_handlers


class WorkerPlugin(GirderPlugin):
    def load(self, info):
        getPlugin('jobs').load(info)

        info['apiRoot'].worker = Worker()

        events.bind('jobs.schedule', 'worker', event_handlers.schedule)
        events.bind('jobs.status.validate', 'worker', event_handlers.validateJobStatus)
        events.bind('jobs.status.validTransitions', 'worker', event_handlers.validTransitions)
        events.bind('jobs.cancel', 'worker', event_handlers.cancel)
        events.bind('model.job.save.after', 'worker', event_handlers.attachJobInfoSpec)
        events.bind('model.job.save', 'worker', event_handlers.attachParentJob)
        Job().exposeFields(AccessType.SITE_ADMIN, {'celeryTaskId', 'celeryQueue'})
