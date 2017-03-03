#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import click
from girder_client import GirderClient


class GirderCli(GirderClient):
    """
    A command line Python client for interacting with a Girder instance's
    RESTful api, specifically for performing uploads into a Girder instance.
    """

    def __init__(self, username, password, host=None, port=None, apiRoot=None,
                 scheme=None, apiUrl=None, apiKey=None):
        """
        Initialization function to create a GirderCli instance, will attempt
        to authenticate with the designated Girder instance. Aside from username, password,
        and apiKey, all other kwargs are passed directly through to the
        :py:class:`girder_client.GirderClient` base class constructor.

        :param username: username to authenticate to Girder instance.
        :param password: password to authenticate to Girder instance, leave
            this blank to be prompted.
        """
        super(GirderCli, self).__init__(
            host=host, port=port, apiRoot=apiRoot, scheme=scheme, apiUrl=apiUrl)
        interactive = password is None

        if apiKey:
            self.authenticate(apiKey=apiKey)
        elif username:
            self.authenticate(username, password, interactive=interactive)


class _DeprecatedOption(click.Option):
    def get_help_record(self, ctx):
        pass


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS)
@click.option('--api-url', default=None,
              help='RESTful API URL '
                   '(e.g https://girder.example.com:443/%s)' % GirderClient.DEFAULT_API_ROOT)
@click.option('--api-key', envvar='GIRDER_API_KEY', default=None,
              help='[default: GIRDER_API_KEY env. variable]')
@click.option('--username', default=None)
@click.option('--password', default=None)
# Deprecated options
@click.option('--host', default=GirderClient.DEFAULT_HOST, show_default=True,
              cls=_DeprecatedOption)
@click.option('--scheme', default=GirderClient.DEFAULT_SCHEME, show_default=True,
              cls=_DeprecatedOption)
@click.option('--port', default=GirderClient.DEFAULT_PORT, show_default=True,
              cls=_DeprecatedOption)
@click.option('--api-root', default=GirderClient.DEFAULT_API_ROOT,
              help='relative path to the Girder REST API', show_default=True,
              cls=_DeprecatedOption)
@click.pass_context
def main(ctx, username, password, api_key, api_url, scheme, host, port, api_root):
    """Perform common Girder CLI operations.

    The CLI is particularly suited to upload (or download) large, nested
    hierarchy of data to (or from) Girder from (or into) a local directory.

    The recommended way to use credentials is to first generate an api key
    and then specify the ``api-key`` argument or set the ``GIRDER_API_KEY``
    environment variable.

    The client also supports ``username`` and ``password`` args. If only the
    ``username`` is specified, the client will prompt the user to interactively
    input his/her password.
    """
    ctx.obj = GirderCli(
        username, password, host=host, port=port, apiRoot=api_root,
        scheme=scheme, apiUrl=api_url, apiKey=api_key)


def _common_parameters(path_exists=False, path_writable=True,
                       additional_parent_types=['collection', 'user']):
    parent_types = ['folder'] + additional_parent_types
    parent_type_cls = click.Option if len(additional_parent_types) > 0 else _DeprecatedOption
    def wrap(func):
        decorators = [
            click.option('--parent-type', default='folder', show_default=True, cls=parent_type_cls,
                         help='type of Girder parent target', type=click.Choice(parent_types)),
            click.argument('parent_id'),
            click.argument(
                'local_folder',
                type=click.Path(exists=path_exists, dir_okay=True,
                                writable=path_writable, readable=True)),
        ]
        for decorator in reversed(decorators):
            func = decorator(func)
        return func
    return wrap

_common_help = 'PARENT_ID is the id of the Girder parent target and ' \
               'LOCAL_FOLDER is the path to the local target folder.'


_short_help = 'Download files from Girder'


@main.command('download', short_help=_short_help, help='%s\n\n%s' % (_short_help, _common_help))
@_common_parameters()
@click.pass_obj
def _download(gc, parent_type, parent_id, local_folder):
    gc.downloadResource(parent_id, local_folder, parent_type)


_short_help = 'Synchronize local folder with remote Girder folder'


@main.command('localsync', short_help=_short_help, help='%s\n\n%s' % (_short_help, _common_help))
@_common_parameters(additional_parent_types=[])
@click.pass_obj
def _localsync(gc, parent_type, parent_id, local_folder):
    if parent_type != 'folder':
        raise Exception('localsync command only accepts parent-type of folder')
    gc.loadLocalMetadata(local_folder)
    gc.downloadFolderRecursive(parent_id, local_folder, sync=True)
    gc.saveLocalMetadata(local_folder)


_short_help = 'Upload files to Girder'


@main.command('upload', short_help=_short_help, help='%s\n\n%s' % (_short_help, _common_help))
@_common_parameters(path_exists=True, path_writable=False)
@click.option('--leaf-folders-as-items', is_flag=True,
              help='upload all files in leaf folders to a single Item named after the folder')
@click.option('--reuse', is_flag=True,
              help='use existing items of same name at same location or create a new one')
@click.option('--dry-run', is_flag=True,
              help='will not write anything to Girder, only report what would happen')
@click.option('--blacklist', default='',
              help='comma-separated list of filenames to ignore')
@click.pass_obj
def _upload(gc, parent_type, parent_id, local_folder,
            leaf_folders_as_items, reuse, blacklist, dry_run):
    gc.upload(
        local_folder, parent_id, parent_type,
        leafFoldersAsItems=leaf_folders_as_items, reuseExisting=reuse,
        blacklist=blacklist.split(','), dryRun=dry_run)


if __name__ == '__main__':
    main()  # pragma: no cover
