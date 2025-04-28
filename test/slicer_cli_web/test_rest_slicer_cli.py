import functools
import json
import os
import time

import pytest
from girder.api import rest
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from pytest_girder.assertions import assertStatusOk

from slicer_cli_web import docker_resource, rest_slicer_cli
from slicer_cli_web.models import CLIItem


@pytest.fixture
def handlerFunc(server, admin, folder, file):
    # Make a request to allow there to be some lingering context to handle the
    # testing outside of a request for the actual handler.
    server.request('/system/version')
    rest.setCurrentUser(admin)

    xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')

    girderCLIItem = Item().createItem('data', admin, folder)
    Item().setMetadata(girderCLIItem, dict(
        slicerCLIType='task', type='python', image='dockerImage',
        digest='dockerImage@sha256:abc', xml=open(xmlpath, 'rb').read()))

    resource = docker_resource.DockerResource('test')
    item = CLIItem(girderCLIItem)
    handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(item)
    yield functools.partial(handlerFunc, resource)


@pytest.fixture
def handlerRerunFuncs(server, admin, folder, file):
    # Make a request to allow there to be some lingering context to handle the
    # testing outside of a request for the actual handler.
    server.request('/system/version')
    rest.setCurrentUser(admin)

    xmlpath = os.path.join(os.path.dirname(__file__), 'data', 'ExampleSpec.xml')

    girderCLIItem = Item().createItem('data', admin, folder)
    Item().setMetadata(girderCLIItem, dict(
        slicerCLIType='task', type='python', image='dockerImage',
        digest='dockerImage@sha256:abc', xml=open(xmlpath, 'rb').read()))

    resource = docker_resource.DockerResource('test')
    item = CLIItem(girderCLIItem)
    handlerFunc = rest_slicer_cli.genHandlerToRunDockerCLI(item)
    handlerRerunFunc = rest_slicer_cli.genHandlerToReRunDockerCLI(item, handlerFunc)
    yield functools.partial(handlerFunc, resource), functools.partial(handlerRerunFunc, resource)


@pytest.mark.plugin('slicer_cli_web')
def test_genHandlerToRunDockerCLI(folder, file, handlerFunc):
    assert handlerFunc is not None

    job = handlerFunc(params={
        'inputImageFile': str(file['_id']),
        'secondImageFile': str(file['_id']),
        'outputStainImageFile_1_folder': str(folder['_id']),
        'outputStainImageFile_1': 'sample1.png',
        'outputStainImageFile_2_folder': str(folder['_id']),
        'outputStainImageFile_2_name': 'sample2.png',
        'stainColor_1': '[0.5, 0.5, 0.5]',
        'stainColor_2': '[0.2, 0.3, 0.4]',
        'returnparameterfile_folder': str(folder['_id']),
        'returnparameterfile': 'output.data',
    })

    kwargs = json.loads(job['kwargs'])
    assert 'container_args' in kwargs
    assert 'image' in kwargs
    assert 'pull_image' in kwargs

    assert kwargs['image'] == 'dockerImage@sha256:abc'
    assert kwargs['pull_image'] == 'if-not-present'
    container_args = kwargs['container_args']
    assert container_args[0] == 'data'


@pytest.mark.plugin('slicer_cli_web')
def test_get_matching_resource(server, admin):
    # Make some resources
    publicFolder = Folder().find({'parentId': admin['_id'], 'name': 'Public'})[0]
    privateFolder = Folder().find({'parentId': admin['_id'], 'name': 'Private'})[0]
    # Create some resources to use in the tests; this was mostly copied from a
    # test in another repo and has more items and folders than needed
    collection = Collection().createCollection(
        'collection A', admin)
    colFolderA = Folder().createFolder(
        collection, 'folder A', parentType='collection',
        creator=admin)
    colFolderB = Folder().createFolder(
        collection, 'folder B', parentType='collection',
        creator=admin)
    colFolderC = Folder().createFolder(
        colFolderA, 'folder C', creator=admin)
    Item().createItem('item A1', admin, colFolderA)
    Item().createItem('item B1', admin, colFolderB)
    Item().createItem('item B2', admin, colFolderB)
    Item().createItem('item C1', admin, colFolderC)
    Item().createItem('item C2', admin, colFolderC)
    Item().createItem('item C3', admin, colFolderC)
    Item().createItem('item Public 1', admin, publicFolder)
    Item().createItem('item Private 1', admin, privateFolder)
    folderD = Folder().createFolder(publicFolder, 'folder D', creator=admin)
    Item().createItem('item D1', admin, folderD)
    itemD2 = Item().createItem('item D2', admin, folderD)
    # Now test
    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'folder',
        'name': '^fold.*D',
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json['name'] == 'folder D'

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'item',
        'name': '^item',
        'path': '^/collection/.*/folder.*/folder',
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json['name'] == 'item C3'

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'item',
        'name': '^item .* 1',
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json['name'] == 'item Private 1'

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'item',
        'name': '^item .* 1',
    })
    assertStatusOk(resp)
    assert resp.json['name'] == 'item Public 1'

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'item',
        'name': 'nosuchitem',
    })
    assertStatusOk(resp)
    assert resp.json is None

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'folder',
        'relative_path': '..',
        'base_type': 'item',
        'base_id': itemD2['_id']
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json['name'] == 'folder D'

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'folder',
        'relative_path': '..',
        'base_type': 'item',
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json is None

    resp = server.request('/slicer_cli_web/path_match', params={
        'type': 'folder',
        'relative_path': '..',
        'base_type': 'item',
        'base_id': 'nosuchid'
    }, user=admin)
    assertStatusOk(resp)
    assert resp.json is None


@pytest.mark.plugin('slicer_cli_web')
def test_girderApiUrl(handlerFunc, folder, file):
    job = handlerFunc(params={
        'inputImageFile': str(file['_id']),
        'secondImageFile': str(file['_id']),
        'outputStainImageFile_1_folder': str(folder['_id']),
        'outputStainImageFile_1': 'sample1.png',
        'outputStainImageFile_2_folder': str(folder['_id']),
        'outputStainImageFile_2_name': 'sample2.png',
        'stainColor_1': '[0.5, 0.5, 0.5]',
        'stainColor_2': '[0.2, 0.3, 0.4]',
        'returnparameterfile_folder': str(folder['_id']),
        'returnparameterfile': 'output.data',
        'girderApiUrl': '',
        'girderToken': '',
    })
    kwargs = json.loads(job['kwargs'])
    assert '--api-url' in kwargs['container_args']
    assert '--girder-token' in kwargs['container_args']


@pytest.mark.parametrize('testParams,results', [
    ({'outputStainImageFile_1': '{{reference_base}}{{extension}}'}, 'Sample.jpg'),
    ({'outputStainImageFile_1': '{{task}}.test.png'}, 'data.test.png'),
    ({'outputStainImageFile_1': '{{title}}.test.png'},
     'Performs Adaptive Color Deconvolution.test.png'),
    ({'outputStainImageFile_1': '{{image}}.test.png'}, 'dockerImage.test.png'),
    ({'outputStainImageFile_1': 'test.{{now}}.png'}, 'test.' + time.strftime('%Y')),
    ({'outputStainImageFile_1': '{{yyyy}}.test.png'}, time.strftime('%Y') + '.test.png'),
    ({'outputStainImageFile_1': '{{parameter_stainColor_1}}.png'}, '0.5, 0.5, 0.5.png'),
    ({'outputStainImageFile_1': '{{parameter_inputImageFile}}.png'}, 'Sample.png'),
    ({'outputStainImageFile_1': '{{parameter_inputImageFile_base}}.png'}, 'Sample.png'),
    ({'outputStainImageFile_1': '{{name}}.png'}, 'outputStainImageFile_1.png'),
    ({'outputStainImageFile_1': '{{label}}.png'}, 'Output image of Stain 1.png'),
    ({'outputStainImageFile_1': '{{description}}.png'}, 'Output Image of Stain 1.png'),
    ({'outputStainImageFile_1': '{{index}}.png'}, '2.png'),
    ({'gamma': '{{default}}0'}, '0.50'),
    ({'gamma': '{{env_GAMMA}}'}, '0.4'),
    ({'gamma': '{{env_NOTGAMMA|default("0.3")}}'}, '0.3'),
    ({'gamma': '{#control:#some_control#}'}, ''),
])
@pytest.mark.plugin('slicer_cli_web')
def test_templateParams(handlerFunc, folder, file, testParams, results):
    os.environ['SLICER_CLI_WEB_GAMMA'] = '0.4'
    job = handlerFunc(params=dict({
        'inputImageFile': str(file['_id']),
        'secondImageFile': str(file['_id']),
        'outputStainImageFile_1_folder': str(folder['_id']),
        'outputStainImageFile_1': 'sample1.png',
        'outputStainImageFile_2_folder': str(folder['_id']),
        'outputStainImageFile_2_name': 'sample2.png',
        'stainColor_1': '[0.5, 0.5, 0.5]',
        'stainColor_2': '[0.2, 0.3, 0.4]',
        'returnparameterfile_folder': str(folder['_id']),
        'returnparameterfile': 'output.data',
    }, **testParams))
    ca = json.loads(job['kwargs'])['container_args']
    assert results in repr(ca)


@pytest.mark.plugin('slicer_cli_web')
def test_genHandlerToReRunDockerCLI(folder, file, handlerRerunFuncs):
    handlerFunc, handlerRerunFunc = handlerRerunFuncs
    assert handlerFunc is not None
    assert handlerRerunFunc is not None

    job = handlerFunc(params={
        'inputImageFile': str(file['_id']),
        'secondImageFile': str(file['_id']),
        'outputStainImageFile_1_folder': str(folder['_id']),
        'outputStainImageFile_1': 'sample1.png',
        'outputStainImageFile_2_folder': str(folder['_id']),
        'outputStainImageFile_2_name': 'sample2.png',
        'stainColor_1': '[0.5, 0.5, 0.5]',
        'stainColor_2': '[0.2, 0.3, 0.4]',
        'returnparameterfile_folder': str(folder['_id']),
        'returnparameterfile': 'output.data',
    })

    rerunJob = handlerRerunFunc(params={'jobId': str(job['_id'])})

    kwargs = json.loads(rerunJob['kwargs'])
    assert 'container_args' in kwargs
    assert 'image' in kwargs
    assert 'pull_image' in kwargs

    assert kwargs['image'] == 'dockerImage@sha256:abc'
    assert kwargs['pull_image'] == 'if-not-present'
    container_args = kwargs['container_args']
    assert container_args[0] == 'data'
