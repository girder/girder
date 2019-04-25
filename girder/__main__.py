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

import cherrypy
import os

try:
    from girder.cli import serve
    import girder
except ImportError:
    # Update python path to ensure server respawning works. See #732
    source_root_dir = os.path.dirname(os.path.dirname(__file__))
    import sys
    cherrypy.engine.log("[Girder] Appending source root dir to 'sys.path': %s"
                        % source_root_dir)
    sys.path.append(source_root_dir)
    from girder.cli import serve
    import girder


if __name__ == '__main__':
    girder.logprint.warning('Deprecation notice: Use "girder serve" to start Girder.')
    serve.main()
