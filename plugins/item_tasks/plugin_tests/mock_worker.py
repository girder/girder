# Mocks job scheduling in order to simulate interaction with the worker.
# This is loaded during the web_client_item_tasks.tasks test.
import girder
import os
import requests
import json


def markAsFinished(job):
    jobInfo = job['kwargs']['jobInfo']

    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.QUEUED
        })
    req.raise_for_status()
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.RUNNING
        })
    req.raise_for_status()
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.SUCCESS
        })
    req.raise_for_status()


def simulateConfigure(job):
    """Simulate worker configuring a docker Slicer CLI item task"""
    output = job['kwargs']['outputs']['_stdout']

    with open(os.path.join(os.path.dirname(__file__), 'slicer_cli.xml'), 'rb') as f:
        xml = f.read()

    # Write the XML output back to the server
    req = requests.request(
        method=output['method'], url=output['url'], headers=output['headers'],
        params=output['params'], data=xml)
    req.raise_for_status()

    # Update the job to mark it as finished
    markAsFinished(job)


def simulateJsonConfigure(job, specs):
    """Simulate worker configuring a docker JSON item task"""
    output = job['kwargs']['outputs']['_stdout']

    with open(os.path.join(os.path.dirname(__file__), specs), 'rb') as f:
        spec = f.read()

    # Write the JSON output back to the server
    req = requests.request(
        method=output['method'], url=output['url'], headers=output['headers'],
        params=output['params'], data=spec)
    req.raise_for_status()

    # Update the job to mark it as finished
    markAsFinished(job)


def simulateRun(job):
    """Simulate worker running the demo task"""
    jobInfo = job['kwargs']['jobInfo']
    # Write the inputs to the log
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.QUEUED
        })
    req.raise_for_status()
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'log': json.dumps(job['itemTaskBindings']['inputs']),
            'status': girder.plugins.jobs.constants.JobStatus.RUNNING
        })
    req.raise_for_status()

    # Update the job to mark it as finished
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.SUCCESS
        })
    req.raise_for_status()


def mockedSchedule(self, job, *args, **kwargs):
    # Configure item/folder from Slicer CLI
    if job['type'].endswith('.item_task_slicer_cli_description'):
        simulateConfigure(job)
    # Configure item/folder from JSON
    elif job['type'].endswith('.item_task_json_description'):
        if job['title'].find('item-tasks-demo') >= 0:
            simulateJsonConfigure(job, os.path.join('..', 'demo', 'demo.json'))
        else:
            simulateJsonConfigure(job, 'specs.json')
    # Execute task
    elif job['type'] == 'item_task':
        simulateRun(job)
    else:
        raise Exception('Unknown job type scheduled: %s' % job['type'])


girder.plugins.jobs.models.job.Job.scheduleJob = mockedSchedule
