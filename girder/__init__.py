from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = None


import logging

from girder.utility import config
from girder.utility._cache import cache, requestCache, rateLimitBuffer


__license__ = 'Apache 2.0'
auditLogger = logging.getLogger('girder_audit')
auditLogger.setLevel(logging.INFO)
auditLogger.propagate = False

config.loadConfig()  # Populate the config info at import time


def _setupCache():
    """
    Setup caching based on configuration file.

    Cache backends are forcibly replaced because Girder initially configures
    the regions with the null backends.
    """
    curConfig = config.getConfig()

    if curConfig['cache']['enabled']:
        # Replace existing backend, this is necessary
        # because they're initially configured with the null backend
        cacheConfig = {
            'cache.global.replace_existing_backend': True,
            'cache.request.replace_existing_backend': True
        }

        curConfig['cache'].update(cacheConfig)

        cache.configure_from_config(curConfig['cache'], 'cache.global.')
        requestCache.configure_from_config(curConfig['cache'], 'cache.request.')
    else:
        # Reset caches back to null cache (in the case of server teardown)
        cache.configure(backend='dogpile.cache.null', replace_existing_backend=True)
        requestCache.configure(backend='dogpile.cache.null', replace_existing_backend=True)

    # Although the rateLimitBuffer has no pre-existing backend, this method may be called multiple
    # times in testing (where caches were already configured)
    rateLimitBuffer.configure(backend='dogpile.cache.memory', replace_existing_backend=True)
