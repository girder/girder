import cherrypy
from dogpile.cache import make_region, register_backend
from dogpile.cache.backends.memory import MemoryBackend


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
rateLimitBuffer = make_region(name='girder.rate_limit')
