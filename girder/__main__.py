#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import sys  # pragma: no cover
import cherrypy  # pragma: no cover

from girder.utility import server  # pragma: no cover

if __name__ == '__main__':  # pragma: no cover
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test = True
    else:
        test = False
    server.setup(test)

    cherrypy.engine.start()
    cherrypy.engine.block()
