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
import sys
import types
from girder_client import GirderClient, HttpError


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
        def _progressBar(*args, **kwargs):
            bar = click.progressbar(*args, **kwargs)
            bar.bar_template = "[%(bar)s]  %(info)s  %(label)s"
            bar.show_percent = True
            bar.show_pos = True

            def formatSize(length):
                if length == 0:
                    return '%.2f' % length
                unit = ''
                # See https://en.wikipedia.org/wiki/Binary_prefix
                units = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
                while True:
                    if length <= 1024 or len(units) == 0:
                        break
                    unit = units.pop(0)
                    length /= 1024.
                return '%.2f%s' % (length, unit)

            def formatPos(_self):
                pos = formatSize(_self.pos)
                if _self.length_known:
                    pos += '/%s' % formatSize(_self.length)
                return pos

            bar.format_pos = types.MethodType(formatPos, bar)
            return bar

        _progressBar.reportProgress = sys.stdout.isatty()

        super(GirderCli, self).__init__(
            host=host, port=port, apiRoot=apiRoot, scheme=scheme, apiUrl=apiUrl,
            progressReporterCls=_progressBar)
        interactive = password is None

        if apiKey:
            self.authenticate(apiKey=apiKey)
        elif username:
            self.authenticate(username, password, interactive=interactive)


class _HiddenOption(click.Option):
    def get_help_record(self, ctx):
        pass


class _AdvancedOption(click.Option):
    pass


class _Group(click.Group):
    def format_options(self, ctx, formatter):
        opts = []
        advanced_opts = []
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is None:
                continue
            if isinstance(param, _AdvancedOption):
                advanced_opts.append(rv)
            else:
                opts.append(rv)

        if opts:
            with formatter.section('Options'):
                formatter.write_dl(opts)
        if advanced_opts:
            with formatter.section('Advanced Options'):
                formatter.write_dl(advanced_opts)
        self.format_commands(ctx, formatter)


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS, cls=_Group)
@click.option('--api-url', default=None,
              help='RESTful API URL '
                   '(e.g https://girder.example.com:443/%s)' % GirderClient.DEFAULT_API_ROOT)
@click.option('--api-key', envvar='GIRDER_API_KEY', default=None,
              help='[default: GIRDER_API_KEY env. variable]')
@click.option('--username', default=None)
@click.option('--password', default=None)
# Advanced options
@click.option('--host', default=None,
              cls=_AdvancedOption,
              help="[default: %s]" % GirderClient.DEFAULT_HOST)
@click.option('--scheme', default=None,
              cls=_AdvancedOption,
              help="[default: %s if %s else %s]" % (
                  GirderClient.getDefaultScheme(GirderClient.DEFAULT_HOST),
                  GirderClient.DEFAULT_HOST,
                  GirderClient.getDefaultScheme("girder.example.com")))
@click.option('--port', default=None,
              cls=_AdvancedOption,
              help="[default: %s if %s; %s if %s else %s]" % (
                  GirderClient.DEFAULT_HTTPS_PORT, "https",
                  GirderClient.DEFAULT_LOCALHOST_PORT, "localhost",
                  GirderClient.DEFAULT_HTTP_PORT,
                  ))
@click.option('--api-root', default=None,
              help='relative path to the Girder REST API '
                   '[default: %s]' % GirderClient.DEFAULT_API_ROOT,
              show_default=True,
              cls=_AdvancedOption)
@click.pass_context
def main(ctx, username, password, api_key, api_url, scheme, host, port, api_root):
    """Perform common Girder CLI operations.

    The CLI is particularly suited to upload (or download) large, nested
    hierarchy of data to (or from) Girder from (or into) a local directory.

    The recommended way to use credentials is to first generate an API key
    and then specify the ``api-key`` argument or set the ``GIRDER_API_KEY``
    environment variable.

    The client also supports ``username`` and ``password`` args. If only the
    ``username`` is specified, the client will prompt the user to interactively
    input his/her password.
    """
    # --api-url and URL by part arguments are mutually exclusive
    url_part_options = ['host', 'scheme', 'port', 'api_root']
    has_api_url = ctx.params.get('api_url', None)
    for name in url_part_options:
        has_url_part = ctx.params.get(name, None)
        if has_api_url and has_url_part:
            raise click.BadArgumentUsage(
                'Option "--api-url" and option "--%s" are mutually exclusive.' %
                name.replace("_", "-"))

    ctx.obj = GirderCli(
        username, password, host=host, port=port, apiRoot=api_root,
        scheme=scheme, apiUrl=api_url, apiKey=api_key)


def _lookup_parent_type(client, object_id):

    object_id = client._checkResourcePath(object_id)

    for parent_type in ['folder', 'collection', 'user', 'item']:
        try:
            client.get('resource/%s/path' % object_id, parameters={'type': parent_type})
            return parent_type
        except HttpError as exc_info:
            if exc_info.status == 400:
                continue
            raise


def _CommonParameters(path_exists=False, path_writable=True,
                      additional_parent_types=('collection', 'user'), path_default=None):
    parent_types = ['folder'] + list(additional_parent_types)
    parent_type_cls = _HiddenOption
    parent_type_default = 'folder'
    if len(additional_parent_types) > 0:
        parent_types.append('auto')
        parent_type_cls = click.Option
        parent_type_default = 'auto'

    def wrap(func):
        decorators = [
            click.option('--parent-type', default=parent_type_default,
                         show_default=True, cls=parent_type_cls,
                         help='type of Girder parent target', type=click.Choice(parent_types)),
            click.argument('parent_id'),
            click.argument(
                'local_folder',
                type=click.Path(exists=path_exists, dir_okay=True,
                                writable=path_writable, readable=True),
                default=path_default
            ),
        ]
        for decorator in reversed(decorators):
            func = decorator(func)
        return func
    return wrap


_common_help = 'PARENT_ID is the id of the Girder parent target and ' \
               'LOCAL_FOLDER is the path to the local target folder.'


_short_help = 'Download files from Girder'


@main.command('download', short_help=_short_help, help='%s\n\n%s' % (
    _short_help, _common_help.replace('LOCAL_FOLDER', 'LOCAL_FOLDER (default: ".")')))
@_CommonParameters(additional_parent_types=['collection', 'user', 'item'], path_default='.')
@click.pass_obj
def _download(gc, parent_type, parent_id, local_folder):
    if parent_type == 'auto':
        parent_type = _lookup_parent_type(gc, parent_id)
    if parent_type == 'item':
        gc.downloadItem(parent_id, local_folder)
    else:
        gc.downloadResource(parent_id, local_folder, parent_type)


_short_help = 'Synchronize local folder with remote Girder folder'


@main.command('localsync', short_help=_short_help, help='%s\n\n%s' % (_short_help, _common_help))
@_CommonParameters(additional_parent_types=[])
@click.pass_obj
def _localsync(gc, parent_type, parent_id, local_folder):
    if parent_type != 'folder':
        raise Exception('localsync command only accepts parent-type of folder')
    gc.loadLocalMetadata(local_folder)
    gc.downloadFolderRecursive(parent_id, local_folder, sync=True)
    gc.saveLocalMetadata(local_folder)


_short_help = 'Upload files to Girder'


@main.command('upload', short_help=_short_help, help='%s\n\n%s' % (_short_help, _common_help))
@_CommonParameters(path_exists=True, path_writable=False)
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
    if parent_type == 'auto':
        parent_type = _lookup_parent_type(gc, parent_id)
    gc.upload(
        local_folder, parent_id, parent_type,
        leafFoldersAsItems=leaf_folders_as_items, reuseExisting=reuse,
        blacklist=blacklist.split(','), dryRun=dry_run)


if __name__ == '__main__':
    main()  # pragma: no cover
