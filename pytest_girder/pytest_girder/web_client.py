import inspect
import os
import six
import subprocess
import time


def _webClientResource():
    from girder.api import access
    from girder.api.describe import describeRoute, Description
    from girder.api.rest import Resource
    from girder.constants import ROOT_DIR, registerAccessFlag
    from girder.exceptions import RestException
    from girder.models.folder import Folder
    from girder.models.upload import Upload
    from girder.plugin import getPlugin
    from girder.utility.progress import ProgressContext

    class _WebClientTestEndpoints(Resource):
        def __init__(self):
            super(_WebClientTestEndpoints, self).__init__()
            self.route('GET', ('progress',), self.testProgress)
            self.route('PUT', ('progress', 'stop'), self.testProgressStop)
            self.route('POST', ('file',), self.uploadFile)
            self.route('POST', ('access_flag',), self.registerAccessFlags)
            self.stop = False

        @access.token
        @describeRoute(
            Description('Test progress contexts from the web')
            .param('test', 'Name of test to run.  These include "success" and "failure".',
                   required=False)
            .param('duration', 'Duration of the test in seconds', required=False, dataType='int')
            .param('resourceId', 'Resource ID associated with the progress notification.',
                   required=False)
            .param('resourceName', 'Type of resource associated with the progress notification.',
                   required=False)
        )
        def testProgress(self, params):
            test = params.get('test', 'success')
            duration = int(params.get('duration', 10))
            resourceId = params.get('resourceId', None)
            resourceName = params.get('resourceName', None)
            startTime = time.time()
            with ProgressContext(True, user=self.getCurrentUser(),
                                 title='Progress Test', message='Progress Message',
                                 total=duration, resource={'_id': resourceId},
                                 resourceName=resourceName) as ctx:
                for current in range(duration):
                    if self.stop:
                        break
                    ctx.update(current=current)
                    wait = startTime + current + 1 - time.time()
                    if wait > 0:
                        time.sleep(wait)
                if test == 'error':
                    raise RestException('Progress error test.')

        @access.token
        @describeRoute(
            Description('Halt all progress tests')
        )
        def testProgressStop(self, params):
            self.stop = True

        @access.user
        @describeRoute(None)
        def uploadFile(self, params):
            """
            Providing this works around a limitation in phantom that makes us
            unable to upload binary files, or at least ones that contain certain
            byte values. The path parameter should be provided relative to the
            root directory of the repository.
            """
            self.requireParams(('folderId', 'path'), params)

            if params['path'].startswith('${'):  # relative to plugin e.g. ${my_plugin}/path
                end = params['path'].find('}')
                plugin = params['path'][2:end]
                plugin = getPlugin(plugin)
                if plugin is None:
                    raise Exception('Invalid plugin %s.' % plugin)
                root = os.path.dirname(inspect.getfile(plugin.__class__))
                path = root + params['path'][end + 1:]
            else:  # assume relative to core package
                path = os.path.join(ROOT_DIR, params['path'])
            name = os.path.basename(path)
            folder = Folder().load(params['folderId'], force=True)

            upload = Upload().createUpload(
                user=self.getCurrentUser(), name=name, parentType='folder',
                parent=folder, size=os.path.getsize(path))

            with open(path, 'rb') as fd:
                file = Upload().handleChunk(upload, fd)

            return file

        @access.public
        @describeRoute(None)
        def registerAccessFlags(self, params):
            """
            Helper that can be used to register access flags in the system. This is
            used to test the access flags UI since the core does not expose any flags.
            """
            flags = self.getBodyJson()
            for key, info in six.viewitems(flags):
                registerAccessFlag(key, info['name'], info['description'], info['admin'])

    return _WebClientTestEndpoints()


def runWebClientTest(boundServer, spec, jasmineTimeout=None):
    """
    Run a web client spec using the phantomjs specRunner.

    :param boundServer: a boundServer fixture.
    :param spec: path to the javascript spec file.
    :param jasmineTimeout: override for jasmine timeout in ms.  This defaults to
        5000ms.
    """
    from girder.constants import ROOT_DIR

    boundServer.root.api.v1.webclienttest = _webClientResource()

    cmd = (
        'npx', 'phantomjs',
        os.path.join(ROOT_DIR, 'girder', 'web_client', 'test', 'specRunner.js'),
        'http://localhost:%s/static/built/testEnv.html' % boundServer.boundPort,
        spec,
        str(jasmineTimeout or ''),
        )

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(
        # https://github.com/bazelbuild/rules_closure/pull/353
        OPENSSL_CONF='/dev/null',
        **os.environ
    ))
    jasmineFinished = False
    for line in iter(p.stdout.readline, b''):
        print(line.rstrip())
        if b'PHANTOM_TIMEOUT' in line or b'error loading source script' in line:
            p.kill()
            raise Exception('Phantomjs failure')
        if b'Testing Finished' in line:
            jasmineFinished = True
    assert p.wait() == 0
    assert jasmineFinished
