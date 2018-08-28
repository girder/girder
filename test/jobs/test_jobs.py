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

import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk
from girder.models.file import File


@pytest.mark.plugin('jobs')
def testConstantsIsDefined(server):
    from girder.plugins.jobs import constants
    assert constants.JobStatus.isValid(constants.JobStatus.SUCCESS) is True


@pytest.mark.plugin('jobs')
def testJobArtifacts(server, admin, user, fsAssetstore):
    from girder.plugins.jobs.models.job import Job
    job = Job().createJob('test', 'test', user=admin)
    url = '/job/%s/artifact' % job['_id']
    params = {
        'name': 'foo',
        'mimeType': 'text/plain',
        'size': 3
    }

    resp = server.request(
        url, method='POST', type='text/plain', body=b'foo', user=user, params=params)
    assertStatus(resp, 403)

    resp = server.request(
        url, method='POST', type='text/plain', body=b'foo', user=admin, params=params)
    assertStatusOk(resp)
    file = resp.json
    assert file['name'] == 'foo'
    assert file['mimeType'] == 'text/plain'

    resp = server.request(url, user=user)
    assertStatus(resp, 403)

    resp = server.request(url, user=admin)
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert resp.json[0]['_id'] == file['_id']

    # Deleting the job should delete the attached artifact
    Job().remove(job)
    assert File().load(file['_id'], force=True) is None
