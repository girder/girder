from girder_jobs.models.job import Job


def wait_for_status(user, job, status):
    """
    Utility to wait for a job model to move into a particular state.
    :param job: The job model to wait on
    :param status: The state to wait for.
    :returns: True if the job model moved into the requested state, False otherwise.
    """
    retries = 0
    jobModel = Job()
    while retries < 10:
        job = jobModel.load(job['_id'], user=user)
        if job['status'] == status:
            return True

    return False
