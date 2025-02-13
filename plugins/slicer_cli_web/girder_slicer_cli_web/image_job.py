from base64 import b64encode
import json
import logging

import docker
from girder_client import GirderClient, HttpError
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job
from girder_worker.app import app

from .models import DockerImageError, DockerImageNotFoundError

logger = logging.getLogger(__name__)


def deleteImage(job):
    """
    Deletes the docker images specified in the job from the local machine.
    Images are forcefully removed (equivalent to docker rmi -f)
    :param job: The job object specifying the docker images to remove from
    the local machine

    """
    job = Job().updateJob(
        job,
        log='Started to Delete Docker images\n',
        status=JobStatus.RUNNING,
    )
    docker_client = None
    try:
        deleteList = job['kwargs']['deleteList']
        error = False

        try:
            docker_client = docker.from_env(version='auto')

        except docker.errors.DockerException as err:
            logger.exception('Could not create the docker client')
            job = Job().updateJob(
                job,
                log='Failed to create the Docker Client\n' + str(err) + '\n',
                status=JobStatus.ERROR,
            )
            raise DockerImageError('Could not create the docker client')

        for name in deleteList:
            try:
                docker_client.images.remove(name, force=True)

            except Exception as err:
                logger.exception('Failed to remove image')
                job = Job().updateJob(
                    job,
                    log='Failed to remove image \n' + str(err) + '\n',
                )
                error = True
        if error is True:
            job = Job().updateJob(
                job,
                log='Failed to remove some images',
                status=JobStatus.ERROR,
                notify=True,
                progressMessage='Errors deleting some images'
            )
        else:
            job = Job().updateJob(
                job,
                log='Removed all images',
                status=JobStatus.SUCCESS,
                notify=True,
                progressMessage='Removed all images'
            )
    except Exception as err:
        logger.exception('Error with job')
        job = Job().updateJob(
            job,
            log='Error with job \n ' + str(err) + '\n',
            status=JobStatus.ERROR,

        )
    finally:
        if docker_client:
            docker_client.close()


def findLocalImage(client, name):
    """
    Checks if the docker image exist locally
    :param name: The name of the docker image

    :returns id: returns the docker image id
    """
    try:
        image = client.images.get(name)
    except Exception:
        return None
    return image.id


def _split_image_and_version(image_name: str) -> tuple[str, str]:
    """
    Splits a docker image name into its name and version (tag or digest).
    """
    if ':' in image_name.split('/')[-1]:
        return image_name.rsplit(':', 1)
    return image_name.rsplit('@', 1)


@app.task(bind=True)
def ingest_from_docker(self, name_list, token: str, folder_id, pull: bool):  # noqa: C901
    """
    Attempts to cache metadata on images in the pull list and load list.
    Images in the pull list are pulled first, then images in both lists are
    queried for there clis and each cli's xml description. The clis and
    xml data is stored in the girder mongo database
    Event Listeners assume the job is done when the job status
     is ERROR or SUCCESS.
    Event listeners check the jobtype to determine if a job is Dockerimage
    related
    """
    stage = 'initializing'
    try:
        print('Started to load Docker images')

        errorState = False

        notExistSet = set()
        try:
            docker_client = docker.from_env(version='auto')
        except docker.errors.DockerException as err:
            print(f'Could not create the docker client: {err}')
            raise DockerImageError('Could not create the docker client')

        pullList = [
            name for name in name_list
            if pull or not findLocalImage(docker_client, name)
        ]
        loadList = [name for name in name_list if name not in pullList]

        try:
            stage = 'pulling'
            pullDockerImage(docker_client, pullList)
        except DockerImageNotFoundError as err:
            errorState = True
            notExistSet = set(err.imageName)
            print('FAILURE: Could not find the following images\n' + '\n'.join(notExistSet))

        stage = 'metadata'
        images, loadingError = loadMetadata(docker_client, pullList, loadList, notExistSet)
        gc = GirderClient(apiUrl=self.request.apiUrl)
        gc.token = token

        for name, cli_dict in images:
            stage = 'parsing'

            docker_image = docker_client.images.get(name)
            tag_metadata = docker_image.labels.copy()

            if 'description' in tag_metadata:
                description = tag_metadata['description']
                del tag_metadata['description']
            else:
                description = 'Slicer CLI generated docker image tag folder'

            tag_metadata = {k.replace('.', '_'): v for k, v in tag_metadata.items()}
            if 'Author' in docker_image.attrs:
                tag_metadata['author'] = docker_image.attrs['Author']

            digest = None
            if docker_image.attrs.get('RepoDigests', []):
                digest = docker_image.attrs['RepoDigests'][0]

            tag_metadata['digest'] = digest
            tag_metadata['slicerCLIType'] = 'tag'

            image_name, tag_name = _split_image_and_version(name)

            try:
                image_folder = gc.post('folder', data={
                    'name': image_name,
                    'parentId': folder_id,
                    'reuseExisting': True,
                    'description': 'Slicer CLI generated docker image folder',
                    'metadata': json.dumps(dict(slicerCLIType='image')),
                })
            except HttpError as err:
                print(f'Error creating image folder {image_name}: {err}')
                print(err.responseText)
                raise

            try:
                tag_folder = gc.post('folder', data={
                    'name': tag_name,
                    'parentId': image_folder['_id'],
                    'reuseExisting': True,
                    'description': description,
                    'metadata': json.dumps(tag_metadata),
                })
            except HttpError as err:
                print(f'Error creating tag folder {tag_name}: {err}')
                print(err.responseText)
                raise

            for cli_name, spec in cli_dict.items():
                try:
                    desc_type = spec.get('desc-type', 'xml')
                    gc.post('slicer_cli_web/cli', data={
                        'folder': tag_folder['_id'],
                        'name': cli_name,
                        'image': name,
                        'replace': True,
                        'desc_type': desc_type,
                        'spec': b64encode(spec[desc_type].encode()),
                    })
                except HttpError as err:
                    print(f'Error creating cli {cli_name}: {err}')
                    print(err.responseText)
                    raise

        if loadingError:
            errorState = True

        print('Finished caching Docker image data')
    except Exception:
        print(f'Error during stage {stage}:')
        raise

    if errorState:
        raise DockerImageError('Error occurred during image loading (see previous output)')


def loadMetadata(docker_client, pullList, loadList, notExistSet):
    """
    Attempt to query preexisting images and pulled images for cli data.
    Cli data for each image is stored and returned as a DockerCache Object

    :param Job(): Singleton JobModel used to update job status
    :param job: The current job being executed
    :param docker_client: An instance of the Docker python client
    :param pullList: The list of images that the job attempted to pull
    :param loadList: The list of images to be queried that were already on the
    local machine
    :notExistSet: A subset of the pullList that didnot exist on the Docker
     registry
    or that could not be pulled

    :returns:DockerCache Object containing cli information for each image
    and a boolean indicating whether an error occurred
    """
    # flag to indicate an error occurred
    errorState = False
    images = []
    for name in pullList:
        if name not in notExistSet:
            print(f'Image {name} was pulled successfully')

            try:
                cli_dict = getCliData(name, docker_client)
                images.append((name, cli_dict))
                print(f'Got pulled image {name} metadata')
            except DockerImageError as err:
                print(f'FAILURE: Error with recently pulled image {name}\n{err}')
                errorState = True

    for name in loadList:
        # create dictionary and load to database
        try:
            cli_dict = getCliData(name, docker_client)
            images.append((name, cli_dict))
            print(f'Loaded metadata from pre-existing local image {name}')
        except DockerImageError as err:
            print(f'FAILURE: Error with recently loading pre-existing image {name}\n{err}')
            errorState = True
    return images, errorState


def getDockerOutput(imgName, command, client):
    """
    Data from each docker image is collected by executing the equivalent of a
    docker run <imgName> <command/args>
    and collecting the output to standard output
    :param imgName: The name of the docker image
    :param command: The commands/ arguments to be passed to the docker image
    :param client: The docker python client
    """
    cont = None
    try:
        cont = client.containers.create(image=imgName, command=command)
        cont.start()
        ret_code = cont.wait()
        if isinstance(ret_code, dict):
            ret_code = ret_code['StatusCode']
        logs = cont.logs(stdout=True, stderr=False, stream=False)
        cont.remove()
    except Exception as err:
        if cont:
            try:
                cont.remove()
            except Exception:
                pass
        logger.exception(
            'Attempt to docker run %s %s failed', imgName, command)
        raise DockerImageError(
            'Attempt to docker run %s %s failed ' % (
                imgName, command) + str(err), imgName)
    if ret_code != 0:
        raise DockerImageError(
            'Attempt to docker run %s %s failed' % (imgName, command), imgName)
    return logs


def getCliData(name, client):
    try:
        cli_dict = getDockerOutput(name, '--list_cli', client)
        # contains nested dict
        # {<cliname>:{type:<type>}}
        try:
            if isinstance(cli_dict, bytes):
                cli_dict = cli_dict.decode('utf8')
            cli_dict = json.loads(cli_dict)
        except Exception:
            print('Failed to parse cli list.  Output of list_cli was\n%r' % cli_dict)
            raise
        for key, info in cli_dict.items():
            desc_type = info.get('desc-type', 'xml')
            cli_desc = getDockerOutput(name, [key, f'--{desc_type}'], client)

            if isinstance(cli_desc, bytes):
                cli_desc = cli_desc.decode('utf8')

            cli_dict[key][desc_type] = cli_desc
            print(f'Got image {name}, cli {key} metadata')
        return cli_dict
    except Exception as err:
        logger.exception(f'Error getting {name} cli data from image')
        raise DockerImageError(f'Error getting {name} cli data from image: {err}')


def pullDockerImage(client, names):
    """
    Attempt to pull the docker images listed in names. Failure results in a
    DockerImageNotFoundError being raised

    :params client: The docker python client
    :params names: A list of docker images to be pulled from the Dockerhub
    """
    imgNotExistList = []
    for name in names:
        try:
            logger.info('Pulling %s image', name)
            client.images.pull(name)
            # some invalid image names will not be pulled but the pull method
            # will not throw an exception so the only way to confirm if a pull
            # succeeded is to attempt a docker inspect on the image
            client.images.get(name)
        except Exception:
            imgNotExistList.append(name)
    if len(imgNotExistList) != 0:
        raise DockerImageNotFoundError('Could not find multiple images ',
                                       image_name=imgNotExistList)
