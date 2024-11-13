#############################################################################
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
#############################################################################

import copy
import json
import os
import re
import time
from base64 import b64decode

import pymongo
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import filtermodel, setRawResponse, setResponseHeader
from girder.api.v1.resource import Resource, RestException
from girder.constants import AccessType, SortDir
from girder.exceptions import AccessException
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.token import Token
from girder.utility import path as path_util
from girder.utility.model_importer import ModelImporter
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from . import TOKEN_SCOPE_MANAGE_TASKS, rest_slicer_cli
from .cli_utils import as_model, get_cli_parameters
from .config import PluginSettings
from .models import CLIItem, DockerImageItem, DockerImageNotFoundError, parser


class DockerResource(Resource):
    """
    Resource object that handles runtime generation and deletion of rest
    endpoints
    """

    jobType = 'slicer_cli_web_job'

    def __init__(self, name):
        super().__init__()
        self.currentEndpoints = {}
        self.resourceName = name
        self.jobType = 'slicer_cli_web_job'
        self.route('PUT', ('docker_image',), self.setImages)
        self.route('POST', ('cli',), self.createOrReplaceCli)
        self.route('DELETE', ('docker_image',), self.deleteImage)
        self.route('GET', ('docker_image',), self.getDockerImages)

        self.route('GET', ('cli',), self.getItems)
        self.route('GET', ('cli', ':id',), self.getItem)
        self.route('DELETE', ('cli', ':id',), self.deleteItem)
        # run is generated per item for better validation
        self.route('GET', ('cli', ':id', 'xml'), self.getItemXML)

        self.route('GET', ('path_match', ), self.getMatchingResource)

        self.route('POST', ('cli', ':id', 'run'), self.runCli)
        self.route('POST', ('cli', ':id', 'rerun'), self.rerunCli)
        self.route('POST', ('cli', ':id', 'datalist', ':key'), self.datalistHandler)

    @access.user
    @autoDescribeRoute(
        Description('Run a Slicer CLI job.')
        .modelParam('id', 'The slicer CLI task item', Item, level=AccessType.READ)
    )
    def runCli(self, item, params):
        user = self.getCurrentUser()
        token = Token().createToken(user=user)
        return cliSubHandler(CLIItem(item), params, user, token).job

    @access.user
    @autoDescribeRoute(
        Description('Re-run a Slicer CLI job.')
        .modelParam('id', 'The slicer CLI item task', Item, level=AccessType.READ)
        .modelParam('jobId', 'The job to re-run', Job, level=AccessType.READ)
    )
    def rerunCli(self, item, job, params):
        user = self.getCurrentUser()
        newParams = job.get('_original_params', {})
        newParams.update(params)

        token = Token().createToken(user=user)
        return cliSubHandler(CLIItem(item), newParams, user, token).job

    @access.user
    @describeRoute(
        Description('Lookup a datalist parameter on a CLI task')
        .modelParam('id', 'The slicer CLI item task', Item, level=AccessType.READ)
        .param('key', 'The parameter name to look up')
        .deprecated()
    )
    def datalistHandler(self, item, key, params):
        # TODO we should change any client that is using this to instead poll the job rather than
        #   waiting for it to finish in the request thread.
        user = self.getCurrentUser()

        currentItem = CLIItem(item)
        token = Token().createToken(user=user)
        job = cliSubHandler(currentItem, params, user, token, key).job
        delay = 0.01
        while job['status'] not in {JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED}:
            time.sleep(delay)
            delay = min(delay * 1.5, 1.0)
            job = Job().load(id=job['_id'], force=True, includeLog=True)
        result = ''.join(job['log']) if 'log' in job else ''
        if '<element' in result:
            result = result[result.index('<element'):]
        if '</element>' in result:
            result = result[:result.rindex('</element>') + 10]
        return result

    @access.public
    @describeRoute(
        Description('List docker images and their CLIs')
        .notes('You must be logged in to see any results.')
    )
    def getDockerImages(self, params):
        data = {}
        if self.getCurrentUser():
            for image in DockerImageItem.findAllImages(self.getCurrentUser()):
                imgData = {}
                for cli in image.getCLIs():
                    basePath = '/%s/cli/%s' % (self.resourceName, cli._id)
                    imgData[cli.name] = {
                        'type': cli.type,
                        'xmlspec': basePath + '/xml',
                        'run': basePath + '/run'
                    }
                data.setdefault(image.image, {})[image.tag] = imgData
        return data

    @access.admin
    @describeRoute(
        Description('Remove a docker image')
        .notes('Must be a system administrator to call this.')
        .param('name', 'The name or a list of names of the docker images to be '
               'removed', required=True)
        .param('delete_from_local_repo',
               'If True the image is deleted from the local repo, requiring '
               'it to be pulled from a remote repository the next time it is '
               'used.  If False the metadata regarding the image is deleted, '
               'but the docker image remains.', required=False,
               dataType='boolean', default=False)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def deleteImage(self, params):
        self.requireParams(('name',), params)
        if 'delete_from_local_repo' in params:
            deleteImage = str(params['delete_from_local_repo']).lower() == 'true'
        else:
            deleteImage = False
        nameList = self.parseImageNameList(params['name'])
        self._deleteImage(nameList, deleteImage)

    def _deleteImage(self, names, deleteImage):
        """
        Removes the docker images and there respective clis endpoints

        :param names: The name of the docker image (user/rep:tag)
        :type name: list
        :param deleteImage: Boolean indicating whether to delete the docker
            image from the local machine.(if True this is equivalent to
            docker rmi -f <image> )
        :type name: boolean
        """
        removed = DockerImageItem.removeImages(names, self.getCurrentUser())
        if removed != names:
            rest = [name for name in names if name not in removed]
            raise RestException('Some docker images could not be removed. %s' % (rest))
        self.deleteImageEndpoints(removed)

        try:
            if deleteImage:
                self._deleteDockerImages(removed)
        except DockerImageNotFoundError as err:
            raise RestException('Invalid docker image name. ' + str(err))

    def _deleteDockerImages(self, removed):
        """
        Creates an asynchronous job to delete the docker images listed in name
        from the local machine
        :param removed:A list of docker image names
        :type removed: list of strings
        """
        job = Job().createLocalJob(
            module='girder_slicer_cli_web.image_job',

            function='deleteImage',
            kwargs={
                'deleteList': removed
            },
            title='Deleting Docker Images',
            user=self.getCurrentUser(),
            type=self.jobType,
            public=True,
            asynchronous=True
        )

        Job().scheduleJob(job)

    def parseImageNameList(self, param):
        """
        Parse a string to get a list of image names.  If the string is a JSON
        list of strings or a JSON string (with quotes), it is processed as
        JSON.  Otherwise, the input value is treated as a single image name.

        :param param: a parameter with an image name, a JSON image name, or a
            JSON list of image names.
        :returns: a list of image names.
        """
        nameList = param
        if isinstance(param, bytes):
            param = param.decode('utf8')
        if isinstance(param, str):
            try:
                nameList = json.loads(param)
            except ValueError:
                pass
        if isinstance(nameList, str):
            nameList = [nameList]
        if not isinstance(nameList, list):
            raise RestException('A valid string or a list of strings is required.')
        for img in nameList:
            if not isinstance(img, str):
                raise RestException('%r is not a valid string.' % img)
            if ':' not in img and '@' not in img:
                raise RestException('Image %s does not have a tag or digest' % img)
        return nameList

    @access.admin(scope=TOKEN_SCOPE_MANAGE_TASKS)
    @describeRoute(
        Description('Add one or a list of images')
        .notes('Must be a system administrator to call this.')
        .param('name', 'A name or a list of names of the docker images to be '
               'loaded', required=True)
        .modelParam('folder', 'The base folder id to upload the tasks to',
                    'folder', paramType='query',
                    level=AccessType.WRITE, required=False)
        .param('pull', 'If True, try to repull all images', paramType='query',
               required=False)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def setImages(self, params):
        """
        Validates the new images to be added (if they exist or not) and then
        attempts to collect xml data to be cached. a job is then called to
        update the girder collection containing the cached docker image data
        """
        self.requireParams(('name',), params)
        nameList = self.parseImageNameList(params['name'])
        folder = params.get('folder', PluginSettings.get_task_folder())
        if not folder:
            raise RestException('no upload folder given or defined by default')
        return self._createPutImageJob(nameList, folder, params.get('pull', None))

    @access.admin(scope=TOKEN_SCOPE_MANAGE_TASKS)
    @filtermodel(Item)
    @autoDescribeRoute(
        Description('Add or replace an item task.')
        .notes('Must be a system administrator to call this.')
        .modelParam('folder', 'The folder ID to upload the task to.', paramType='formData',
                    model=Folder, level=AccessType.WRITE)
        .param('image', 'The docker image identifier.')
        .param('name', 'The name of the item to create or replace.')
        .param('replace', 'Whether to replace an existing item with this name.', dataType='boolean')
        .param('spec', 'Base64-encoded XML spec of the CLI.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def createOrReplaceCli(self, folder: dict, image: str, name: str, replace: bool, spec: str):
        try:
            spec = b64decode(spec).decode()
        except ValueError:
            raise RestException('The CLI spec must be base64-encoded UTF-8.')

        item = Item().createItem(
            name, creator=self.getCurrentUser(), folder=folder, reuseExisting=replace
        )
        metadata = dict(
            slicerCLIType='task',
            type='Unknown',  # TODO does "type" matter behaviorally? If so get it from the client
            digest=None,  # TODO should we support this?
            image=image,
            **parser._parse_xml_desc(item, self.getCurrentUser(), spec)
        )
        return Item().setMetadata(item, metadata)

    def _createPutImageJob(self, nameList, baseFolder, pull=False):
        # TODO convert this to a celery job rather than local job.
        job = Job().createLocalJob(
            module='girder_slicer_cli_web.image_job',
            function='jobPullAndLoad',
            kwargs={
                'nameList': nameList,
                'folder': baseFolder['_id'] if isinstance(baseFolder, dict) else baseFolder,
                'pull': pull,
            },
            title='Pulling and caching docker images',
            type=self.jobType,
            user=self.getCurrentUser(),
            public=True,
            asynchronous=True
        )
        Job().scheduleJob(job)
        return job

    def storeEndpoints(self, imgName, cliName, undoFunction):
        """
        Information on each rest endpoint is saved so they can be
        deleted when docker images are removed or loaded.

        :param imgName: The full name of the docker image with the tag.
            This name must match exactly with the name the command
            docker images displays in the console
        :type imgName: string
        :param cliName: The name of the cli whose rest endpoint is being stored. The
            cli must match exactly with what the docker image returns when
            running <docker image> --list_cli
        :type cliName: string
        """
        img = self.currentEndpoints.setdefault(imgName, {})
        img[cliName] = undoFunction

    def deleteImageEndpoints(self, imageList=None):

        if imageList is None:
            imageList = self.currentEndpoints.keys()
        for imageName in list(imageList):
            for undoFunction in self.currentEndpoints.pop(imageName, {}).values():
                undoFunction()

    def _generateAllItemEndPoints(self):
        # sort by name and creation date desc
        items = sorted(CLIItem.findAllItems(), key=lambda x: (x.restPath, x.item['created']),
                       reverse=True)

        seen = set()
        for item in items:
            # default if not seen yet
            rest_slicer_cli.genRESTEndPointsForSlicerCLIsForItem(
                self, item, item.restPath not in seen
            )
            seen.add(item.restPath)

    def addRestEndpoints(self, event):
        """
        Determines if the job event being triggered is due to the caching of
        new docker images or deleting a docker image off the local machine.  If
        a new image is being loaded all old rest endpoints are deleted and
        endpoints for all cached docker images are regenerated.

        :param event: An event dictionary
        """
        job = event.info['job']

        if job['type'] == self.jobType and job['status'] == JobStatus.SUCCESS:
            self.deleteImageEndpoints()
            self._generateAllItemEndPoints()

    def _dump(self, item, details=False):
        r = {
            '_id': item._id,
            'name': item.name,
            'type': item.type,
            'image': item.image,
            'description': item.item['description']
        }
        if details:
            r['xml'] = item.item['meta']['xml']
        return r

    @access.user
    @autoDescribeRoute(
        Description('List CLIs')
        .errorResponse('You are not logged in.', 403)
        .modelParam('folder', 'The base folder to look for tasks', 'folder', paramType='query',
                    level=AccessType.WRITE, required=False)
    )
    def getItems(self, folder):
        items = CLIItem.findAllItems(self.getCurrentUser(), baseFolder=folder)
        return [self._dump(item) for item in items]

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.READ)
    )
    def getItem(self, item):
        return self._dump(CLIItem(item), True)

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.WRITE)
    )
    def deleteItem(self, item):
        Item().remove(item)
        return dict(status='OK')

    @access.user
    @autoDescribeRoute(
        Description('Get a specific CLI')
        .errorResponse('You are not logged in.', 403)
        .modelParam('id', 'The task item', 'item',
                    level=AccessType.READ)
    )
    def getItemXML(self, item):
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return CLIItem(item).xml

    @access.public
    @autoDescribeRoute(
        Description(
            'Get the most recently updated resource that has a name and path '
            'that matches a regular expression')
        .notes('This can be very slow if name is too general.')
        .param('name', 'A regular expression to match the name of the '
               'resource.', required=False)
        .param('path', 'A regular expression to match the entire resource path.', required=False)
        .param('relative_path', 'A relative resource path to the base item.', required=False)
        .param('base_id', 'The base girder id for the relative path', required=False)
        .param('base_type', 'The base girder type for the relative path', required=False)
        .param('type', 'The type of the resource (item, file, etc.).')
        .errorResponse('Invalid resource type.')
        .errorResponse('No matches.')
    )
    def getMatchingResource(self, name, path, type, relative_path, base_id, base_type):  # noqa: C901 E501
        user = self.getCurrentUser()
        model = ModelImporter.model(type)
        pattern = None
        if path:
            pattern = re.compile(path)
        if relative_path:
            if not base_id or not base_type:
                return None
            try:
                base_model = ModelImporter.model(base_type).load(base_id, user=user)
                base_path = path_util.getResourcePath(base_type, base_model, user=user)
                new_path = os.path.normpath(os.path.join(base_path, relative_path))
                doc = path_util.lookUpPath(new_path, user=user)['document']
                doc['_path'] = new_path.split('/')[2:]
                if type == 'folder':
                    doc['_path'] = doc['_path'][:-1]
            except Exception:
                return None
            if not name and not path:
                return doc
            pattern = re.compile('(?=^' + re.escape(new_path) + ').*' + (path or ''))
        try:
            for doc in model.findWithPermissions(
                    {'name': {'$regex': name}} if name else {},
                    sort=[('updated', SortDir.DESCENDING), ('created', SortDir.DESCENDING)],
                    user=user, level=AccessType.READ, timeout=10000):
                try:
                    resourcePath = path_util.getResourcePath(type, doc, user=user)
                    if not pattern or pattern.search(resourcePath):
                        doc['_path'] = resourcePath.split('/')[2:]
                        if type == 'folder':
                            doc['_path'] = doc['_path'][:-1]
                        return doc
                except (AccessException, TypeError):
                    pass
        except pymongo.errors.ExecutionTimeout:
            return None
        return None


def cliSubHandler(cliItem, params, user, token, datalistKey=None):
    """
    Create a job for a Slicer CLI item and schedule it.

    :param currentItem: a CLIItem model.
    :param params: parameter dictionary passed to the endpoint.
    :param user: user model for the current user.
    :param token: allocated token for the job.
    :param datalistKey: if not None, a param name for this CLI that has a datalist.
    """
    from .girder_worker_plugin.direct_docker_run import run

    clim = as_model(cliItem.xml)
    cliTitle = clim.title

    original_params = copy.deepcopy(params)
    index_params, opt_params, simple_out_params = get_cli_parameters(clim)

    datalistSpec = {
        param.name: json.loads(param.datalist)
        for param in index_params + opt_params
        if param.channel != 'output' and param.datalist
    }

    container_args = [cliItem.name]
    reference = {'slicer_cli_web': {
        'title': cliTitle,
        'image': cliItem.image,
        'name': cliItem.name,
    }}
    now = time.localtime()
    templateParams = {
        'title': cliTitle,  # e.g., "Detects Nuclei"
        'task': cliItem.name,  # e.g., "NucleiDetection"
        'image': cliItem.image,  # e.g., "dsarchive/histomicstk:latest"
        'now': time.strftime('%Y%m%d-%H%M%S', now),
        'yyyy': time.strftime('%Y', now),
        'mm': time.strftime('%m', now),
        'dd': time.strftime('%d', now),
        'HH': time.strftime('%H', now),
        'MM': time.strftime('%M', now),
        'SS': time.strftime('%S', now),
    }

    has_simple_return_file = bool(simple_out_params)
    sub_index_params, sub_opt_params = index_params, opt_params

    if datalistKey:
        datalist = datalistSpec[datalistKey]
        params = params.copy()
        params.update(datalist)
        sub_index_params = [
            param if param.name not in datalist or not rest_slicer_cli.is_on_girder(param)
            else rest_slicer_cli.stringifyParam(param)
            for param in index_params
            if (param.name not in datalist or datalist.get(param.name) is not None)
            and param.name not in {k + rest_slicer_cli.FOLDER_SUFFIX for k in datalist}
        ]
        sub_opt_params = [
            param if param.name not in datalist or not rest_slicer_cli.is_on_girder(param)
            else rest_slicer_cli.stringifyParam(param)
            for param in opt_params
            if param.channel != 'output' and (
                param.name not in datalist or datalist.get(param.name) is not None)
            and param.name not in {k + rest_slicer_cli.FOLDER_SUFFIX for k in datalist}
        ]

    args, result_hooks, primary_input_name = rest_slicer_cli.prepare_task(
        params, user, token, sub_index_params, sub_opt_params,
        has_simple_return_file, reference, templateParams=templateParams)
    container_args.extend(args)

    jobType = '%s#%s' % (cliItem.image, cliItem.name)

    if primary_input_name:
        jobTitle = '%s on %s' % (cliTitle, primary_input_name)
    else:
        jobTitle = cliTitle

    job_kwargs = cliItem.item.get('meta', {}).get('docker-params', {})
    job = run.delay(
        girder_user=user,
        girder_job_type=jobType,
        girder_job_title=jobTitle,
        girder_result_hooks=result_hooks,
        image=cliItem.digest,
        pull_image='if-not-present',
        container_args=container_args,
        **job_kwargs
    )
    jobRecord = Job().load(job.job['_id'], force=True)
    job.job['_original_params'] = jobRecord['_original_params'] = original_params
    job.job['_original_name'] = jobRecord['_original_name'] = cliItem.name
    job.job['_original_path'] = jobRecord['_original_path'] = cliItem.restBasePath
    Job().save(jobRecord)
    return job
