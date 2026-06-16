from girder.plugin import GirderPlugin
from girder.utility import setting_utilities


class PluginSettings:
    SLURM_ACCOUNT = 'worker_slurm.account'
    SLURM_QOS = 'worker_slurm.qos'
    SLURM_MEM = 'worker_slurm.mem'
    SLURM_CPUS = 'worker_slurm.cpus'
    SLURM_NTASKS = 'worker_slurm.ntasks'
    SLURM_PARTITION = 'worker_slurm.partition'
    SLURM_TIME = 'worker_slurm.time'
    SLURM_GRES_CONFIG = 'worker_slurm.gres_config'
    # GPU Settings
    SLURM_GPU = 'worker_slurm.gpu'
    SLURM_GPU_PARTITION = 'worker_slurm.gpu_partition'


class WorkerSlurmPlugin(GirderPlugin):
    DISPLAY_NAME = 'Worker Slurm'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        @setting_utilities.validator({
            PluginSettings.SLURM_ACCOUNT,
            PluginSettings.SLURM_QOS,
            PluginSettings.SLURM_MEM,
            PluginSettings.SLURM_CPUS,
            PluginSettings.SLURM_NTASKS,
            PluginSettings.SLURM_PARTITION,
            PluginSettings.SLURM_TIME,
            PluginSettings.SLURM_GRES_CONFIG,
            PluginSettings.SLURM_GPU,
            PluginSettings.SLURM_GPU_PARTITION,
        })
        def validateSlurmSettings(doc):
            # TODO: add validation
            pass
