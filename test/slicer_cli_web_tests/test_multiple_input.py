import functools
import io
import json
import os

import cherrypy
import pytest
from slicer_cli_web import docker_resource, rest_slicer_cli
from slicer_cli_web.models import CLIItem

from girder.api import rest
from girder.models.item import Item
from girder.models.token import Token
from girder.models.upload import Upload


@pytest.fixture
def seriesFiles(folder, admin, fsAssetstore):
    files = []
    for idx in range(2):
        sampleData = b'Sample %d' % idx
        files.append(Upload().uploadFromFile(
            obj=io.BytesIO(sampleData), size=len(sampleData),
            name='Series%d.dcm' % idx, parentType='folder', parent=folder,
            user=admin))
    yield files


@pytest.fixture
def multipleHandlerFunc(server, admin, folder):
    # Make a request to allow there to be some lingering context to handle the
    # testing outside of a request for the actual handler.
    server.request('/system/version')
    rest.setCurrentUser(admin)
    cherrypy.request.params['token'] = Token().createToken(admin)['_id']

    xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'MultipleSpec.xml')

    girderCLIItem = Item().createItem('multi', admin, folder)
    Item().setMetadata(girderCLIItem, dict(
        slicerCLIType='task', type='python', image='dockerImage',
        digest='dockerImage@sha256:abc', xml=open(xmlpath, 'rb').read()))

    resource = docker_resource.DockerResource('test')
    item = CLIItem(girderCLIItem)
    handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(item)
    yield functools.partial(handlerFunc, resource)


@pytest.mark.plugin('slicer_cli_web')
def test_multiple_input_fans_out(folder, seriesFiles, multipleHandlerFunc):
    job = multipleHandlerFunc(params={
        'inputSeries': '%s,%s' % (seriesFiles[0]['_id'], seriesFiles[1]['_id']),
        'outputImage_folder': str(folder['_id']),
        'outputImage': 'out.png',
    })

    # The job title uses the first file of the list as the primary input
    assert job['title'] == 'Assembles A Series on Series0.dcm'

    kwargs = json.loads(job['kwargs'])
    container_args = kwargs['container_args']
    # cli name, one argument covering the whole series, and the output path
    assert len(container_args) == 3
    serialized = repr(container_args[1])
    assert str(seriesFiles[0]['_id']) in serialized
    assert str(seriesFiles[1]['_id']) in serialized


@pytest.mark.plugin('slicer_cli_web')
def test_multiple_input_comma_in_name(folder, admin, fsAssetstore, multipleHandlerFunc):
    # A comma is legal in a Girder file name but is also the delimiter of the
    # joined container-path argument, so it must not survive into the mounted
    # filename.
    sampleData = b'Sample'
    commaFile = Upload().uploadFromFile(
        obj=io.BytesIO(sampleData), size=len(sampleData), name='Series,part.dcm',
        parentType='folder', parent=folder, user=admin)

    job = multipleHandlerFunc(params={
        'inputSeries': str(commaFile['_id']),
        'outputImage_folder': str(folder['_id']),
        'outputImage': 'out.png',
    })

    serialized = repr(json.loads(job['kwargs'])['container_args'][1])
    assert 'Series_part.dcm' in serialized
    assert 'Series,part.dcm' not in serialized
