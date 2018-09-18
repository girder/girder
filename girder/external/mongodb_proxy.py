"""
Copyright 2013 Gustav Arngarden

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import time
import pymongo

def get_methods(*objs):
    return set(
        attr
        for obj in objs
        for attr in dir(obj)
        if not attr.startswith('_')
           and hasattr(getattr(obj, attr), '__call__')
    )

try:
    # will fail to import from older versions of pymongo
    from pymongo import MongoClient, MongoReplicaSetClient
except ImportError:
    MongoClient, MongoReplicaSetClient = None, None

EXECUTABLE_MONGO_METHODS = get_methods(pymongo.collection.Collection,
                                       pymongo.database.Database,
                                       pymongo.cursor.Cursor,
                                       pymongo.command_cursor.CommandCursor,
                                       MongoClient, MongoReplicaSetClient,
                                       pymongo)


class Executable(object):
    """ Wrap a MongoDB-method and handle AutoReconnect-exceptions
    using the safe_mongocall decorator.
    """

    def __init__(self, method, logger, wait_time=None):
        self.method = method
        self.logger = logger
        # MongoDB's documentation claims that replicaset elections
        # shouldn't take more than a minute. In our experience, we've
        # seen them take as long as a minute and a half, so regardless
        # of what the documentation says, we're going to give the
        # connection two minutes to recover.
        self.wait_time = wait_time or 120

    def __call__(self, *args, **kwargs):
        """ Automatic handling of AutoReconnect-exceptions.
        """
        start = time.time()
        i = 0
        while True:
            try:
                val = self.method(*args, **kwargs)

                # If we get back a cursor, we need to also make sure it tries
                # to auto-reconnect on failure.
                if isinstance(val, (pymongo.cursor.Cursor, pymongo.command_cursor.CommandCursor)):
                    return MongoProxy(val, self.logger, self.wait_time)
                else:
                    return val
            except pymongo.errors.AutoReconnect:
                end = time.time()
                delta = end - start
                if delta >= self.wait_time:
                    break
                self.logger.warning('AutoReconnecting, try %d (%.1f seconds)'
                                    % (i, delta))
                time.sleep(min(5, pow(2, i)))
                i += 1
        # Try one more time, but this time, if it fails, let the
        # exception bubble up to the caller.
        return self.method(*args, **kwargs)

    def __dir__(self):
        return dir(self.method)

    def __str__(self):
        return self.method.__str__()

    def __repr__(self):
        return self.method.__repr__()

class MongoProxy(object):
    """ Proxy for MongoDB connection.
    Methods that are executable, i.e find, insert etc, get wrapped in an
    Executable-instance that handles AutoReconnect-exceptions transparently.

    """
    def __init__(self, conn, logger=None, wait_time=None):
        """ conn is an ordinary MongoDB-connection.

        """
        if logger is None:
            import logging
            logger = logging.getLogger(__name__)

        self.conn = conn
        self.logger = logger
        self.wait_time = wait_time


    def __getitem__(self, key):
        """ Create and return proxy around the method in the connection
        named "key".

        """
        item = self.conn[key]
        if hasattr(item, '__call__'):
            return MongoProxy(item, self.logger, self.wait_time)
        return item

    def __getattr__(self, key):
        """ If key is the name of an executable method in the MongoDB connection,
        for instance find or insert, wrap this method in Executable-class that
        handles AutoReconnect-Exception.

        """

        attr = getattr(self.conn, key)
        if hasattr(attr, '__call__'):
            if key in EXECUTABLE_MONGO_METHODS:
                return Executable(attr, self.logger, self.wait_time)
            else:
                return MongoProxy(attr, self.logger, self.wait_time)
        return attr

    def __call__(self, *args, **kwargs):
        return self.conn(*args, **kwargs)

    def __dir__(self):
        return dir(self.conn)

    def __iter__(self):
        return self.conn.__iter__()

    def __str__(self):
        return self.conn.__str__()

    def __repr__(self):
        return self.conn.__repr__()

    def __nonzero__(self):
        return True
