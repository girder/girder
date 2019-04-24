# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2017 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import girder
from girder.utility import server

cherrypy.config.update({'engine.autoreload.on': False,
                        'environment': 'embedded'})
cherrypy.config['server'].update({'disable_event_daemon': True})

# TODO The below line can be removed if we do away with girder.logprint
girder._quiet = True  # This means we won't duplicate messages to stdout/stderr
_formatter = girder.LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
_handler = cherrypy._cplogging.WSGIErrorHandler()
_handler.setFormatter(_formatter)
girder.logger.addHandler(_handler)

# 'application' is the default callable object for WSGI implementations, see PEP 3333 for more.
server.setup()
application = cherrypy.tree

cherrypy.server.unsubscribe()
cherrypy.engine.start()
