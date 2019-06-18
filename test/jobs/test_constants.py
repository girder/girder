import pytest

from girder_jobs import constants


@pytest.mark.plugin('jobs')
def testConstantsIsDefined(server):
    assert constants.JobStatus.isValid(constants.JobStatus.SUCCESS) is True
