import json
import os

import pytest
from girder_jobs.constants import JobStatus

from pytest_girder.assertions import assertStatus
from pytest_girder.utils import getResponseBody

from .conftest import splitName

DOCKER_SOCKET = '/var/run/docker.sock'
SKIP_DOCKER_TESTS = not os.path.exists(DOCKER_SOCKET)

dockerOnly = pytest.mark.skipif(SKIP_DOCKER_TESTS, reason='Docker socket not found')


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testAddNonExistentImage(images):
    # add a bad image
    img_name = 'null/null:null'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.ERROR)
    images.assertNoImages()


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testDockerAdd(images, boundServer):
    # try to cache a good image to the mongo database
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    # If checked without a user, we should get an empty list
    resp = boundServer.request(path='/slicer_cli_web/docker_image')
    assertStatus(resp, 200)
    assert json.loads(getResponseBody(resp)) == {}
    images.endpointsExist(img_name, ['Example1', 'Example2', 'Example3'], ['NotAnExample'])
    images.deleteImage(img_name, True)
    images.assertNoImages()


# Pure parameter validation; it never contacts docker or the worker.
@pytest.mark.plugin('slicer_cli_web')
def testDockerAddBadParam(boundServer, admin, folder):
    # test sending bad parameters to the PUT endpoint
    kwargs = {
        'path': '/slicer_cli_web/docker_image',
        'user': admin,
        'method': 'PUT',
        'params': {'name': json.dumps(6), 'folder': folder['_id']}
    }
    resp = boundServer.request(**kwargs)
    assertStatus(resp, 400)
    assert 'A valid string' in resp.json['message']

    kwargs['params']['name'] = json.dumps({'abc': 'def'})
    resp = boundServer.request(**kwargs)
    assertStatus(resp, 400)
    assert 'A valid string' in resp.json['message']

    kwargs['params']['name'] = json.dumps([6])
    resp = boundServer.request(**kwargs)
    assertStatus(resp, 400)
    assert 'is not a valid string' in resp.json['message']

    kwargs['params']['name'] = '"not json'
    resp = boundServer.request(**kwargs)
    assertStatus(resp, 400)
    assert 'does not have a tag' in resp.json['message']


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testDockerAddList(images):
    # try to cache a good image to the mongo database
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage([img_name], JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True)
    images.assertNoImages()


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testDockerAddWithoutVersion(images):
    # all images need a version or hash
    img_name = 'girder/slicer_cli_web'
    images.assertNoImages()
    images.addImage(img_name, None, 400)
    images.assertNoImages()


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testDockerDelete(images):
    # just delete the metadata in the mongo database
    # don't delete the docker image
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True, False)
    images.imageIsLoaded(img_name, exists=False)
    images.assertNoImages()


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testDockerDeleteFull(images):
    # Delete the metadata and ask to delete the image off the local machine.
    # Removing the image from the local docker repository is currently a no-op
    # in the server (see DockerResource._deleteDockerImages), so this only
    # asserts that the metadata and endpoints are removed.
    img_name = 'girder/slicer_cli_web:small'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    images.deleteImage(img_name, True, True, JobStatus.SUCCESS)

    images.imageIsLoaded(img_name, exists=False)
    images.assertNoImages()


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testBadImageDelete(images):
    # attempt to delete a non existent image
    img_name = 'null/null:null'
    images.assertNoImages()
    images.deleteImage(img_name, False, )


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testXmlEndpoint(images, boundServer, admin):
    # loads an image and attempts to run an arbitrary xml endpoint

    img_name = 'girder/slicer_cli_web:small'
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)

    name, tag = splitName(img_name)
    data = images.getEndpoint()
    for tag in data.values():
        for cli in tag.values():
            for info in cli.values():
                route = info['xmlspec']
                resp = boundServer.request(
                    path=route,
                    user=admin,
                    isJson=False)
                assertStatus(resp, 200)
                xmlString = getResponseBody(resp)
                # TODO validate with xml schema
                assert xmlString != ''
    images.deleteImage(img_name, True, )


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testEndpointDeletion(images, boundServer, admin):
    img_name = 'girder/slicer_cli_web:small'
    images.addImage(img_name, JobStatus.SUCCESS)
    images.imageIsLoaded(img_name, True)
    data = images.getEndpoint()
    images.deleteImage(img_name, True)
    name, tag = splitName(img_name)

    for tag in data.values():
        for cli in tag.values():
            for info in cli.values():
                route = info['xmlspec']
                resp = boundServer.request(
                    path=route,
                    user=admin,
                    isJson=False)
                # xml route should have been deleted
                assertStatus(resp, 400)


@dockerOnly
@pytest.mark.plugin('slicer_cli_web')
def testAddBadImage(images):
    # job should fail gracefully after pulling the image
    img_name = 'library/hello-world:latest'
    images.assertNoImages()
    images.addImage(img_name, JobStatus.ERROR)
    images.assertNoImages()
