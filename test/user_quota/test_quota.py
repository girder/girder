import json
import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder.models.user import User
from girder_jobs.models.job import Job


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('user_quota')
def testQuotaEnforcedOutsideHierarchy(server, admin, user, fsAssetstore):
    # Set quota on the user
    resp = server.request('/user/%s/quota' % user['_id'], method='PUT', user=admin, params={
        'policy': json.dumps({
            'fileSizeQuota': 1,
            'useQuotaDefault': False
        })
    })
    assertStatusOk(resp)

    job = Job().createJob('test', 'test', user=user)
    url = '/job/%s/artifact' % job['_id']
    params = {
        'name': 'foo',
        'mimeType': 'text/plain',
        'size': 3
    }

    resp = server.request(
        url, method='POST', type='text/plain', body=b'foo', user=user, params=params)
    assertStatus(resp, 400)
    assert resp.json['message'] == ('Upload would exceed file storage quota (need 3 B, '
                                    'only 1 B available - used 0 B out of 1 B)')
    assert resp.json['type'] == 'validation'
    assert resp.json['field'] == 'size'


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('user_quota')
def testAttachedFilesCountTowardQuota(server, admin, user, fsAssetstore):
    resp = server.request('/user/%s/quota' % user['_id'], method='PUT', user=admin, params={
        'policy': json.dumps({
            'fileSizeQuota': 1,
            'useQuotaDefault': False
        })
    })
    assertStatusOk(resp)
    user = User().load(user['_id'], force=True)
    assert user['size'] == 0

    job = Job().createJob('test', 'test', user=user)
    url = '/job/%s/artifact' % job['_id']
    params = {
        'name': 'onebyte.txt',
        'mimeType': 'text/plain',
        'size': 1
    }
    # First should succeed
    resp = server.request(
        url, method='POST', type='text/plain', body=b'0', user=user, params=params)
    assertStatusOk(resp)
    fileId = resp.json['_id']
    user = User().load(user['_id'], force=True)
    assert user['size'] == 1

    # Second should fail since the first counts toward the quota
    resp = server.request(
        url, method='POST', type='text/plain', body=b'0', user=user, params=params)
    assertStatus(resp, 400)
    assert resp.json['message'] == ('Upload would exceed file storage quota (need 1 B, '
                                    'only 0 B available - used 1 B out of 1 B)')
    assert resp.json['type'] == 'validation'
    assert resp.json['field'] == 'size'

    # Deleting the artifact file should decrease the used space
    resp = server.request('/file/%s' % fileId, method='DELETE', user=user)
    assertStatusOk(resp)
    user = User().load(user['_id'], force=True)
    assert user['size'] == 0
