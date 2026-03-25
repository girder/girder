# The path that will be mounted in docker containers for data IO
DOCKER_DATA_VOLUME = '/mnt/girder_worker/data'

# The path that will be mounted in docker containers for utility scripts
DOCKER_SCRIPTS_VOLUME = '/mnt/girder_worker/scripts'


# Settings where plugin information is stored
class PluginSettings:
    API_URL = 'worker.api_url'
    DIRECT_PATH = 'worker.direct_path'
