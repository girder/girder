# Mocks job scheduling in order to simulate interaction with the worker.
# This is loaded during the web_client_item_tasks.tasks test.
import girder
import os
import requests


def simulateConfigure(job):
    """Simulate worker configuring a docker Slicer CLI item task"""
    output = job['kwargs']['outputs']['_stdout']
    jobInfo = job['kwargs']['jobInfo']

    with open(os.path.join(os.path.dirname(__file__), 'slicer_cli.xml'), 'rb') as f:
        xml = f.read()

    # Write the XML output back to the server
    req = requests.request(
        method=output['method'], url=output['url'], headers=output['headers'],
        params=output['params'], data=xml)
    req.raise_for_status()

    # Update the job to mark it as finished
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.SUCCESS
        })
    req.raise_for_status()


def simulateJsonConfigure(job):
    """Simulate worker configuring a docker JSON item task"""
    output = job['kwargs']['outputs']['_stdout']
    jobInfo = job['kwargs']['jobInfo']

    with open(os.path.join(os.path.dirname(__file__), 'specs.json'), 'rb') as f:
        spec = f.read()

    # Write the JSON output back to the server
    req = requests.request(
        method=output['method'], url=output['url'], headers=output['headers'],
        params=output['params'], data=spec)
    req.raise_for_status()

    # Update the job to mark it as finished
    req = requests.request(
        method=jobInfo['method'], url=jobInfo['url'], headers=jobInfo['headers'], params={
            'status': girder.plugins.jobs.constants.JobStatus.SUCCESS
        })
    req.raise_for_status()


def simulateRun(job):
    """Simulate worker running a docker item task"""
    pass


def mockedSchedule(self, job, *args, **kwargs):
    if job['type'] == 'item_task.slicer_cli':
        simulateConfigure(job)
    elif job['type'] == 'item_task.json_description':
        simulateJsonConfigure(job)
    elif job['type'] == 'item_task':
        simulateRun(job)
    else:
        raise Exception('Unknown job type scheduled: %s' % job['type'])


girder.plugins.jobs.models.job.Job.scheduleJob = mockedSchedule
