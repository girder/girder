# -*- coding: utf-8 -*-
from girder_jobs.models.job import Job


def run(job):
    Job().updateJob(job, log='job ran!')


def fail(job):
    Job().updateJob(job, log='job failed')
