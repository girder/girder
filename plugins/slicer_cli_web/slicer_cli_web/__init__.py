#############################################################################
#  Copyright Kitware Inc.
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
#############################################################################

# These two imports must be in this order for appropriate side effects

# isort: off

from . import ctk_cli_adjustment  # noqa

from ctk_cli import CLIArgumentParser  # noqa

# isort: on


from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _importlib_version

try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass

__license__ = 'Apache 2.0'

TOKEN_SCOPE_MANAGE_TASKS = 'slicer_cli_web.manage_tasks'
