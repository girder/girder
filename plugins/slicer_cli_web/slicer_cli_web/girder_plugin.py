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

import datetime
import json
import logging
from pathlib import Path

from girder import events
from girder.constants import AccessType, TokenScope
from girder.plugin import GirderPlugin, getPlugin, registerPluginStaticContent
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from . import TOKEN_SCOPE_MANAGE_TASKS
from .docker_resource import DockerResource
from .models import DockerImageItem

logger = logging.getLogger(__name__)


def _onUpload(event):
    try:
        ref = json.loads(event.info.get('reference'))
    except (ValueError, TypeError):
        return

    if isinstance(ref, dict) and ref.get('type') == 'slicer_cli.parameteroutput':
        job = Job().load(ref['jobId'], force=True, exc=True)

        file = event.info['file']

        # Add link to job model to the output item
        Job().updateJob(job, otherFields={
            'slicerCLIBindings.outputs.parameters': file['_id']
        })


class SlicerCLIWebPlugin(GirderPlugin):
    DISPLAY_NAME = 'Slicer CLI Web'

    def load(self, info):
        try:
            getPlugin('worker').load(info)
        except Exception:
            logger.info('Girder worker is unavailable')

        registerPluginStaticContent(
            'slicer_cli_web',
            css=['/style.css'],
            js=['/girder-plugin-slicer-cli-web.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )

        TokenScope.describeScope(
            TOKEN_SCOPE_MANAGE_TASKS, name='Manage Slicer CLI tasks',
            description='Create / edit Slicer CLI docker tasks', admin=True)

        DockerImageItem.prepare()

        # resource name must match the attribute added to info[apiroot]
        resource = DockerResource('slicer_cli_web')
        info['apiRoot'].slicer_cli_web = resource

        Job().exposeFields(level=AccessType.READ, fields={'slicerCLIBindings'})

        events.bind('data.process', 'slicer_cli_web', _onUpload)

        count = 0
        for job in Job().find({
            'status': {'$in': [
                JobStatus.INACTIVE, JobStatus.QUEUED, JobStatus.RUNNING,
                # from girder_worker, but we don't strictly require its
                # existence
                820, 821, 822, 823, 824,
            ]},
            'updated': {'$lt': datetime.datetime.utcnow() - datetime.timedelta(days=7)}
        }, force=True):
            try:
                Job().updateJob(job, log='Canceled stale job.', status=JobStatus.CANCELED)
                count += 1
            except Exception:
                pass
        if count:
            logger.info('Marking %d old job(s) as cancelled' % count)
