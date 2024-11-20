import cherrypy
from dogpile.cache import make_region, register_backend
from dogpile.cache.backends.memory import MemoryBackend


def _setupCache(curConfig: dict):
    """
    Setup caching based on the provided configuration.

    Cache backends are forcibly replaced because Girder initially configures
    the regions with the null backends.
    """
    from girder.settings import SettingKey
    from girder.models.setting import Setting

    if Setting().get(SettingKey.CACHE_ENABLED):
        # Replace existing backend. This is necessary
        # because they're initially configured with the null backend.
        # The other values here can be overridden by the CACHE_CONFIG setting object.
        cacheConfig = {
            'cache.global.replace_existing_backend': True,
            'cache.request.replace_existing_backend': True,
            'cache.global.backend': 'dogpile.cache.memory',
            'cache.request.backend': 'cherrypy_request',
        }

        cacheConfig.update(Setting().get(SettingKey.CACHE_CONFIG))

        cache.configure_from_config(cacheConfig, 'cache.global.')
        requestCache.configure_from_config(cacheConfig, 'cache.request.')
    else:
        # Reset caches back to null cache (in the case of server teardown)
        cache.configure(backend='dogpile.cache.null', replace_existing_backend=True)
        requestCache.configure(backend='dogpile.cache.null', replace_existing_backend=True)

    # Although the rateLimitBuffer has no pre-existing backend, this method may be called multiple
    # times in testing (where caches were already configured)
    rateLimitBuffer.configure(backend='dogpile.cache.memory', replace_existing_backend=True)


class CherrypyRequestBackend(MemoryBackend):
    """
    A memory backed cache for individual CherryPy requests.

    This provides a cache backend for dogpile.cache which is designed
    to work in a thread-safe manner using cherrypy.request, a thread local
    storage that only lasts for the duration of a request.
    """

    def __init__(self, arguments):
        pass

    @property
    def _cache(self):
        if not hasattr(cherrypy.request, '_girderCache'):
            cherrypy.request._girderCache = {}

        return cherrypy.request._girderCache


register_backend('cherrypy_request', 'girder.utility._cache', 'CherrypyRequestBackend')

# These caches must be configured with the null backend upon creation due to the fact
# that user-based configuration of the regions doesn't happen until server start, which
# doesn't occur when using Girder as a library.
cache = make_region(name='girder.cache').configure(backend='dogpile.cache.null')
requestCache = make_region(name='girder.request').configure(backend='dogpile.cache.null')

# This cache is not configurable by the user, and will always be configured when the server is.
# It holds data for rate limiting, which is ephemeral, but must be persisted (i.e. it's not optional
# or best-effort).
# TODO we need to make this configurable to be share-nothing in a multi-process environment
rateLimitBuffer = make_region(name='girder.rate_limit').configure(backend='dogpile.cache.memory')
