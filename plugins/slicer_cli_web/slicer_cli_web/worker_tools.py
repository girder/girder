import datetime
import logging
import queue
import subprocess
import threading
import time

import yaml
from girder import events
from girder.models.file import File
from girder.models.item import Item
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from .config import PluginSettings

_workerConfig = None
_commandQueue = None
logger = logging.getLogger(__name__)


class CommandQueue(threading.Thread):
    def __init__(self):
        super().__init__()

        self.daemon = True
        self.terminate = False
        self.queue = queue.Queue()
        self.cond = threading.Condition()

    def run(self):
        while not self.terminate:
            try:
                cmd = self.queue.get(block=False)
                logger.info('Running %s' % cmd)
                out = subprocess.check_output(cmd, shell=True)
                logger.info('Ran %s, got %s' % (cmd, out.decode()))
            except queue.Empty:
                with self.cond:
                    self.cond.wait()
            except Exception:
                logger.exception('Exception when running %s' % cmd)

    def add(self, cmd):
        with self.cond:
            self.queue.put(cmd)
            self.cond.notify()

    def stop(self):
        with self.cond:
            self.terminate = True
            self.cond.notify()

    def __del__(self):
        self.stop()


def _loadWorkerConfig():  # noqa
    """
    Load and update the config file.
    """
    global _commandQueue, _workerConfig

    item = PluginSettings.get_worker_config_item()
    if item is None or len(list(Item().childFiles(item, limit=2))) != 1:
        _workerConfig = 'none'
        return
    try:
        file = next(Item().childFiles(item))
        if (isinstance(_workerConfig, dict)
                and file['_id'] == _workerConfig['file']['_id']
                and file.get('updated', file.get('created')) == _workerConfig['file'].get(
                    'updated', _workerConfig['file'].get('created'))):
            return
        with File().open(file) as fptr:
            config = yaml.safe_load(fptr)
        if not len(config['workers']) >= 1:
            raise Exception('At least one worker must be specified.')
        for entry in config['workers']:
            if 'start' not in entry or 'stop' not in entry:
                raise Exception('All workers must have start and stop values.')
            if 'concurrency' in entry and (
                    int(entry['concurrency']) != entry['concurrency'] or entry['concurrency'] < 1):
                raise Exception('Workers that specify concurrency must be a positive integer.')
        if 'idle-time' in config and not isinstance(config['idle-time'], dict):
            raise Exception('The idle-time entry must be a dictionary.')
    except Exception:
        logger.exception('Failed to load slicer_cli_web worker config item.')
        _workerConfig = 'none'
        return

    stopAll = False
    if not _commandQueue:
        _commandQueue = CommandQueue()
        _commandQueue.start()
    if not isinstance(_workerConfig, dict):
        _workerConfig = {'active': 0, 'start': datetime.datetime.utcnow()}
        # We ask for all workers to stop when we first load a config file
        if config.get('initial-stop') is not False:
            stopAll = True
    _workerConfig['file'] = file
    _workerConfig['workers'] = config['workers']
    _workerConfig['maxConcurrency'] = sum(
        worker.get('concurrency', 1) for worker in config['workers'])
    _workerConfig['idle-time'] = config.get('idle-time', {})
    _workerConfig['idle-time'].setdefault('all', 300)
    _workerConfig['started'] = {
        val for val in _workerConfig.get('started', [])
        if val >= 0 and val < len(config['workers'])}
    logger.info(
        'Loaded slicer_cli_web worker config item with %d worker(s) and %d maxConcurrency',
        len(_workerConfig['workers']), _workerConfig['maxConcurrency'])
    if stopAll:
        for idx in range(len(_workerConfig['workers'])):
            _stopWorker(idx)
    return True


def _startWorker():
    """
    Start any worker.
    """
    for idx in range(len(_workerConfig['workers'])):
        if idx not in _workerConfig['started']:
            cmd = _workerConfig['workers'][idx]['start']
            _workerConfig['started'] |= {idx}
            _commandQueue.add(cmd)
            return


def _stopWorker(idx):
    """
    Stop a worker absed on its index
    """
    cmd = _workerConfig['workers'][idx]['stop']
    _workerConfig['started'] -= {idx}
    _commandQueue.add(cmd)


def _delayStop():
    """
    After a delay, see if we still need to stop.
    """
    if isinstance(_workerConfig, dict):
        _workerConfig.pop('waitThread', None)
        _manageWorkers()


def _stopAllWorkers():
    """
    Check if enough time has passed.  If so, stop all workers.
    """
    if _workerConfig.get('waitThread'):
        return
    delay = 0
    try:
        delay = float(_workerConfig['idle-time']['all'])
    except Exception:
        delay = 300
    delay -= time.time() - _workerConfig['lastChange']
    if delay > 0:
        _workerConfig['waitThread'] = threading.Timer(delay, _delayStop)
        _workerConfig['waitThread'].daemon = True
        _workerConfig['waitThread'].start()
        return
    for worker in list(_workerConfig['started']):
        _stopWorker(worker)


def _manageWorkers(event=None):
    """
    Handle an event that requires us to check on worker managerment.
    """
    if _workerConfig is None:
        _loadWorkerConfig()
    if not isinstance(_workerConfig, dict):
        return
    activeJobs = Job().find({
        'handler': 'celery_handler',
        'status': {'$not': {'$in': [
            JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED
        ]}},
        'updated': {'$gte': _workerConfig['start']}
    }).count()

    if activeJobs == _workerConfig['active']:
        if not activeJobs and len(_workerConfig['started']):
            _stopAllWorkers()
        return
    logger.info('Now have %d active job(s) (was %d)' % (activeJobs, _workerConfig['active']))
    _workerConfig['lastChange'] = time.time()
    startedConcurrency = sum(
        _workerConfig['workers'][idx].get('concurrency', 1) for idx in _workerConfig['started'])
    # Start a worker if we have more active jobs than workers and any workers
    # are unstarted.
    if (activeJobs > startedConcurrency
            and min(activeJobs, _workerConfig['maxConcurrency']) > startedConcurrency):
        _startWorker()
    elif not activeJobs:
        _stopAllWorkers()
    _workerConfig['active'] = activeJobs


def _manageWorkersConfig(event):
    """
    Handle an event where the worker configuration may have changed.
    """
    if event.info.get('key') != PluginSettings.SLICER_CLI_WEB_WORKER_CONFIG_ITEM:
        return
    if _loadWorkerConfig():
        _manageWorkers(None)


def _manageWorkersConfigFile(event):
    """
    Handle an event where the worker configuration file may have changed.
    """
    if not isinstance(_workerConfig, dict) or event.info['_id'] != _workerConfig['file']['_id']:
        return
    if _loadWorkerConfig():
        _manageWorkers(None)


def start():
    """
    Add event bindings and start worker management tools.
    """
    events.bind('jobs.cancel', 'slicer_cli_web_worker', _manageWorkers)
    events.bind('jobs.schedule', 'slicer_cli_web_worker', _manageWorkers)
    events.bind('jobs.job.update.after', 'slicer_cli_web_worker', _manageWorkers)
    events.bind('model.job.save.after', 'slicer_cli_web_worker', _manageWorkers)

    events.bind('model.setting.save.after', 'slicer_cli_web_worker', _manageWorkersConfig)
    events.bind('model.file.save.after', 'slicer_cli_web_worker', _manageWorkersConfigFile)
    _manageWorkers(None)
