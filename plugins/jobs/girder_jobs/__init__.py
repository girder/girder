# -*- coding: utf-8 -*-
import importlib

from girder import events
from girder.plugin import GirderPlugin
from girder.utility.model_importer import ModelImporter

from . import constants, job_rest
from .models.job import Job


def scheduleLocal(event):
    """
    Jobs whose handler is set to "local" will be run on the Girder server. They
    should contain a "module" field that specifies which python module should
    be executed, and optionally a "function" field to declare what function
    within that module should be executed. If no "function" field is specified,
    the function is assumed to be named "run". The function will be passed the
    args and kwargs of the job.
    """
    job = event.info

    if job['handler'] == constants.JOB_HANDLER_LOCAL:
        if 'module' not in job:
            raise Exception('Locally scheduled jobs must have a module field.')

        module = importlib.import_module(job['module'])
        fn = getattr(module, job.get('function', 'run'))
        fn(job)


class JobsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Jobs'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        ModelImporter.registerModel('job', Job, 'jobs')
        info['apiRoot'].job = job_rest.Job()
        events.bind('jobs.schedule', 'jobs', scheduleLocal)
