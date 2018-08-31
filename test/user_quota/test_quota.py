import json
import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.mark.plugin('jobs')
@pytest.mark.plugin('user_quota')
def testQuotaEnforcedOutsideHierarchy(server, admin, user, fsAssetstore):
    from girder.plugins.jobs.models.job import Job

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
