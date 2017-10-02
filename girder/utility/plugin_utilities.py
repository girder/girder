###############################################################################
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
###############################################################################

import six
from stevedore.extension import ExtensionManager
from stevedore.named import NamedExtensionManager
from toposort import toposort_flatten

NAMESPACE = 'girder.plugin'


class config(object):  # noqa: class name
    """
    Wrap a plugin's ``load`` method appending plugin metadata.

    :param name str: The plugin's name
    :param description str: A brief description of the plugin.
    :param version str: A semver compatible version string.
    :param dependencies list: A list of plugins required by this plugin.
    :returns: A decorator that appends the metadata to the method
    """
    def __init__(self, **kw):
        self.config = kw

    def __call__(self, func):
        @six.wraps(func)
        def wrapped(*arg, **kw):
            return func(*arg, **kw)
        wrapped.config = self.config
        return wrapped


def getPluginConfig(plugin):
    # TODO: Handle errors?
    mgr = NamedExtensionManager(
        namespace=NAMESPACE,
        names=[plugin],
        warn_on_missing_entrypoint=True
    )
    config = getattr(mgr[plugin].plugin, 'config', {})
    defaultConfig = {
        'name': plugin,
        'description': '',
        'url': '',
        'version': '',
        'dependencies': [],
        'staticWebDependencies': set()
    }
    return dict(defaultConfig, **config)


def getPluginDependencies(plugin):
    try:
        config = getPluginConfig(plugin)
    except Exception:
        config = {}

    return set(config.get('dependencies', []))


def loadPlugins(plugins, root, appconf, apiRoot=None):
    info = {
        'config': appconf,
        'serverRoot': root,
        'apiRoot': apiRoot
    }

    mgr = NamedExtensionManager(
        namespace=NAMESPACE,
        names=plugins,
        invoke_on_load=True,
        invoke_args=(info,),
        warn_on_missing_entrypoint=True,
        verify_requirements=True
    )
    return mgr.names()


def findAllPlugins():
    mgr = ExtensionManager(namespace=NAMESPACE)
    return {
        plugin: getPluginConfig(plugin) for plugin in mgr.names()
    }


def getToposortedPlugins(plugins, ignoreMissing=True):
    depTree = {
        plugin: getPluginDependencies(plugin) for plugin in plugins
    }
    return toposort_flatten(depTree)


def getPluginFailureInfo():
    return {}
