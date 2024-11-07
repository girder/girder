import os
import select
import uuid

import docker
from docker.errors import DockerException

from girder_worker import logger


def select_loop(exit_condition=lambda: True, readers=None, writers=None):
    """
    Run a select loop for a set of readers and writers

    :param exit_condition: A function to evaluate to determine if the select
        loop should terminate if all pipes are empty.
    :type exit_condition: function
    :param readers: The list of ReaderStreamConnector's that will be added to the
        select call.
    :type readers: list
    :param writers: The list of WriteStreamConnector's that will be added to the
        select call.
    :type writers: list
    """

    BUF_LEN = 65536

    try:
        while True:
            # We evaluate this first so that we get one last iteration of
            # of the loop before breaking out of the loop.
            exit = exit_condition()

            open_writers = [writer for writer in writers if writer.fileno() is not None]

            # get ready pipes, timeout of 100 ms
            readable, writable, _ = select.select(readers, open_writers, (), 0.1)

            for ready in readable:
                read = ready.read(BUF_LEN)
                if read == 0:
                    readers.remove(ready)

            for ready in writable:
                # TODO for now it's OK for the input reads to block since
                # input generally happens first, but we should consider how to
                # support non-blocking stream inputs in the future.
                written = ready.write(BUF_LEN)
                if written == 0:
                    writers.remove(ready)

            need_opening = [writer for writer in writers if writer.fileno() is None]
            for connector in need_opening:
                connector.open()

            # all pipes empty?
            empty = (not readers or not readable) and (not writers or not writable)

            if (empty and exit):
                break

    finally:
        for stream in readers + writers:
            stream.close()


CONTAINER_PATH = '/mnt/girder_worker/data'


def chmod_writable(host_paths):
    """
    Since files written by docker containers are owned by root, we can't
    clean them up in the worker process since that typically doesn't run
    as root. So, we run a lightweight container to make the temp dir cleanable.
    """
    if not isinstance(host_paths, (list, tuple)):
        host_paths = (host_paths,)

    if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
        timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
        client = docker.from_env(version='auto', timeout=timeout)
    else:
        client = docker.from_env(version='auto')

    config = {
        'tty': True,
        'volumes': {},
        'detach': False,
        'remove': True
    }

    container_paths = []
    for host_path in host_paths:
        container_path = os.path.join(CONTAINER_PATH, uuid.uuid4().hex)
        container_paths.append(container_path)
        config['volumes'][host_path] = {
            'bind': container_path,
            'mode': 'rw'
        }

    args = ['chmod', '-R', 'a+rw'] + container_paths

    try:
        client.containers.run('busybox:latest', args, **config)
    except DockerException:
        logger.exception('Error setting perms on docker volumes %s.' % host_paths)
        raise
