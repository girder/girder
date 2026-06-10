#!/usr/bin/env python
import logging
import sys
import types
from http.client import HTTPConnection

import click
import requests
from girder_client import GirderClient, __version__
from requests.adapters import HTTPAdapter

_logger = logging.getLogger('girder_client.cli')


class GirderCli(GirderClient):
    """
    A command line Python client for interacting with a Girder instance's
    RESTful api, specifically for performing uploads into a Girder instance.
    """

    def __init__(self, username, password, host=None, port=None, apiRoot=None,
                 scheme=None, apiUrl=None, apiKey=None, sslVerify=True, token=None,
                 retries=None):
        """
        Initialization function to create a GirderCli instance, will attempt
        to authenticate with the designated Girder instance. Aside from username, password,
        apiKey, and sslVerify, all other kwargs are passed directly through to the
        :py:class:`girder_client.GirderClient` base class constructor.

        :param username: username to authenticate to Girder instance.
        :param password: password to authenticate to Girder instance, leave
            this blank to be prompted.
        :param sslVerify: disable SSL verification or specify path to certfile on
            :class:`requests.Session` object.
        :param token: An authentication token to use.
        """
        def _progressBar(*args, **kwargs):
            bar = click.progressbar(*args, **kwargs)
            bar.bar_template = '[%(bar)s]  %(info)s  %(label)s'
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
                if _self.length is not None:
                    pos += '/%s' % formatSize(_self.length)
                return pos

            bar.format_pos = types.MethodType(formatPos, bar)
            return bar

        _progressBar.reportProgress = sys.stdout.isatty()

        super().__init__(
            host=host, port=port, apiRoot=apiRoot, scheme=scheme, apiUrl=apiUrl,
            progressReporterCls=_progressBar)
        interactive = password is None

        self.sslVerify = sslVerify
        self.retries = retries

        if token:
            self.setToken(token)

        if apiKey:
            self.authenticate(apiKey=apiKey)
        elif username:
            self.authenticate(username, password, interactive=interactive)

    def sendRestRequest(self, *args, **kwargs):
        with self.session() as session:
            session.verify = self.sslVerify
            if self.retries:
                session.mount(self.urlBase, HTTPAdapter(max_retries=self.retries))
            return super().sendRestRequest(*args, **kwargs)


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
@click.option('-v', '--verbose', count=True,
              help='Enable verbose mode (use multiple to increase verbosity)')
# Advanced options
@click.option('--host', default=None,
              cls=_AdvancedOption,
              help='[default: %s]' % GirderClient.DEFAULT_HOST)
@click.option('--scheme', default=None,
              cls=_AdvancedOption,
              help='[default: %s if %s else %s]' % (
                  GirderClient.getDefaultScheme(GirderClient.DEFAULT_HOST),
                  GirderClient.DEFAULT_HOST,
                  GirderClient.getDefaultScheme('girder.example.com')))
@click.option('--port', default=None,
              cls=_AdvancedOption,
              help='[default: %s if %s; %s if %s else %s]' % (
                  GirderClient.DEFAULT_HTTPS_PORT, 'https',
                  GirderClient.DEFAULT_LOCALHOST_PORT, 'localhost',
                  GirderClient.DEFAULT_HTTP_PORT,
                  ))
@click.option('--api-root', default=None,
              help='relative path to the Girder REST API '
                   '[default: %s]' % GirderClient.DEFAULT_API_ROOT,
              show_default=True,
              cls=_AdvancedOption)
@click.option('--no-ssl-verify', is_flag=True, default=False,
              help='Disable SSL Verification',
              show_default=True,
              cls=_AdvancedOption
              )
@click.option('--ca-certificate', default=None,
              help='Specify path to CA certificate to use to verify the server',
              show_default=True,
              cls=_AdvancedOption
              )
@click.option('--token', default=None,
              help='Authentication token to use',
              show_default=True,
              cls=_AdvancedOption)
@click.option('--retries', default=None, type=click.INT,
              help='Number of times to retry failed requests',
              cls=_AdvancedOption)
@click.version_option(version=__version__, prog_name='Girder command line interface')
@click.pass_context
def main(ctx, username, password,
         api_key, api_url, scheme, host, port, api_root,
         no_ssl_verify, ca_certificate, token, retries, verbose):
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
    _set_logging_level(verbose)

    # --api-url and URL by part arguments are mutually exclusive
    url_part_options = ['host', 'scheme', 'port', 'api_root']
    has_api_url = ctx.params.get('api_url', None)
    for name in url_part_options:
        has_url_part = ctx.params.get(name, None)
        if has_api_url and has_url_part:
            raise click.BadArgumentUsage(
                'Option "--api-url" and option "--%s" are mutually exclusive.' %
                name.replace('_', '-'))
    if ca_certificate and no_ssl_verify:
        raise click.BadArgumentUsage(
            'Option "--no-ssl-verify" and option "--ca-certificate" are mutually exclusive.')

    ssl_verify = True
    if ca_certificate:
        ssl_verify = ca_certificate
    if no_ssl_verify:
        ssl_verify = False

    ctx.obj = GirderCli(
        username, password, host=host, port=port, apiRoot=api_root,
        scheme=scheme, apiUrl=api_url, apiKey=api_key, sslVerify=ssl_verify, token=token,
        retries=retries)


def _set_logging_level(verbosity):
    if not verbosity:
        level = logging.ERROR
    if verbosity == 1:
        level = logging.WARNING
    elif verbosity == 2:
        level = logging.INFO
    elif verbosity >= 3:
        HTTPConnection.debuglevel = 1
        level = logging.DEBUG

    requestsLogger = logging.getLogger('requests.packages.urllib3')
    girderClientLogger = logging.getLogger('girder_client')
    for logger in (requestsLogger, girderClientLogger):
        logger.addHandler(logging.StreamHandler(sys.stderr))
        logger.setLevel(level)


def _lookup_parent_type(client, object_id):

    object_id = client._checkResourcePath(object_id)

    for parent_type in ['folder', 'collection', 'user', 'item', 'file']:
        try:
            client.get('resource/%s/path' % object_id, parameters={'type': parent_type})
            return parent_type
        except requests.HTTPError as exc_info:
            if exc_info.response.status_code == 400:
                continue
            raise


def _CommonParameters(path_exists=False, path_writable=True,
                      additional_parent_types=('collection', 'user'),
                      path_default=None, multiple_local=False):
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
                default=path_default,
                nargs=1 if not multiple_local else -1,
                required=multiple_local
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
@_CommonParameters(additional_parent_types=[
    'collection', 'user', 'item', 'file'], path_default='.')
@click.option('--skip', type=click.Choice(['path', 'size', 'hash'], case_sensitive=False),
              default=None, help='Conditionally skip downloading files. '
              'Specify which type of check to perform. ("path": skip if file path exists, '
              '"size": skip if file size is the same, "hash": skip if file hash is the same). '
              '[default: None]')
@click.pass_obj
def _download(gc, parent_type, parent_id, local_folder, skip):
    if parent_type == 'auto':
        parent_type = _lookup_parent_type(gc, parent_id)
    if parent_type == 'item':
        gc.downloadItem(parent_id, local_folder, skip=skip)
    elif parent_type == 'file':
        gc.downloadFile(parent_id, local_folder, skip=skip)
    else:
        gc.downloadResource(parent_id, local_folder, parent_type, skip=skip)


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


@main.command('upload', short_help=_short_help, help='%s\n\n%s' % (
    _short_help,
    'PARENT_ID is the id of the Girder parent target and '
    'LOCAL_FOLDER is one or more paths to local folders or files.'))
@_CommonParameters(path_exists=True, path_writable=False, multiple_local=True)
@click.option('--leaf-folders-as-items', is_flag=True,
              help='upload all files in leaf folders to a single Item named after the folder')
@click.option('--reuse', is_flag=True,
              help='use existing items of same name at same location or create a new one')
@click.option('--dry-run', is_flag=True,
              help='will not write anything to Girder, only report what would happen')
@click.option('--blacklist', default='',
              help='comma-separated list of filenames to ignore')
@click.option('--reference', default=None,
              help='optional reference to send along with the upload')
@click.pass_obj
def _upload(gc, parent_type, parent_id, local_folder,
            leaf_folders_as_items, reuse, blacklist, dry_run, reference):
    if parent_type == 'auto':
        parent_type = _lookup_parent_type(gc, parent_id)
    gc.upload(
        local_folder, parent_id, parent_type,
        leafFoldersAsItems=leaf_folders_as_items, reuseExisting=reuse,
        blacklist=blacklist.split(','), dryRun=dry_run, reference=reference)


_short_help = 'List contents of a user, collection, folder, item, or file'
_long_help = """
PARENT_ID is the id of a Girder user, collection, folder, item, or file.
The command first shows the requested resource so opaque ids are identifiable,
then lists any immediate child resources: users and collections contain folders,
folders contain folders and items, items contain files, and files have no
children. In JSON output, the requested resource is emitted as this_record.

Examples:

    # List USER: jon.crall
    girder-client --api-url https://data.kitware.com/api/v1 list 598a19658d777f7d33e9c18b

    # List COLLECTION: VIAME
    girder-client --api-url https://data.kitware.com/api/v1 list 58b747ec8d777f0aef5d0f6a

    # List FOLDER: kwimage_demodata
    girder-client --api-url https://data.kitware.com/api/v1 list 647cfb2ca71cc6eae69303a4

    # List ITEM: the paraview.png logo
    girder-client --api-url https://data.kitware.com/api/v1 list 647cfb97a71cc6eae69303b5

    # List FILE: the paraview.png logo
    girder-client --api-url https://data.kitware.com/api/v1 list 647cfb97a71cc6eae69303b6
""".rstrip()


@main.command('list', short_help=_short_help, help='%s\n\n%s' % (_short_help, _long_help))
@click.option('--parent-type', default='auto', show_default=True,
              help='type of Girder parent target',
              type=click.Choice(['folder', 'collection', 'user', 'item', 'file', 'auto']))
@click.argument('parent_id')
@click.option('--limit', default=None, type=click.INT,
              help='maximum number of records to list')
@click.option('--offset', default=None, type=click.INT,
              help='starting offset into list')
@click.option('--json', 'as_json', default=False, is_flag=True, show_default=True,
              help='output machine-readable JSON')
@click.pass_obj
def _list(gc, parent_type, parent_id, limit, offset, as_json):
    if parent_type == 'auto':
        parent_type = _list_lookup_parent_type(gc, parent_id)

    this_record = _list_get_resource(gc, parent_type, parent_id)

    if as_json:
        from girder_client._jsonemitter import _JSONEmitter
        emitter = _JSONEmitter()
        emitter.start_dict()
    else:
        emitter = None

    _list_record_info(gc, this_record, emitter)

    if parent_type in {'collection', 'user'}:
        # Collections and users can have folder children.
        child_types = ['folder']
    elif parent_type == 'folder':
        # Folders can have folders and items as children.
        child_types = ['folder', 'item']
    elif parent_type == 'item':
        # The requested item is already shown as this_record; list its files.
        child_types = ['file']
    elif parent_type == 'file':
        # Files have no children.
        child_types = []
    else:
        raise KeyError(parent_type)

    if child_types:
        _list_children_info(gc, parent_id, parent_type,
                            child_types, limit, offset, emitter)

    if emitter:
        emitter.end_dict()


def _list_lookup_parent_type(gc, parent_id):
    """
    Resolve the Girder resource type for the list command.

    The shared _lookup_parent_type helper uses the resource path endpoint,
    which can fail to identify users. Fall back to direct resource GETs, and
    for users also try listing folders with parentType=user because some Girder
    deployments allow traversing a user's public folders without allowing the
    user record itself to be read anonymously.
    """
    lookup_errors = []
    try:
        parent_type = _lookup_parent_type(gc, parent_id)
    except requests.HTTPError as exc_info:
        lookup_errors.append('resource path lookup: %s' % _list_http_error_summary(exc_info))
    else:
        if parent_type is not None:
            return parent_type
        lookup_errors.append('resource path lookup: no match')

    for candidate_type in ['folder', 'collection', 'item', 'file']:
        try:
            _list_get_resource(gc, candidate_type, parent_id)
            return candidate_type
        except requests.HTTPError as exc_info:
            if exc_info.response.status_code in {400, 403, 404}:
                lookup_errors.append('%s: %s' % (
                    candidate_type, _list_http_error_summary(exc_info)))
                continue
            raise

    user_status = _list_probe_user_resource(gc, parent_id)
    if user_status is True:
        return 'user'
    lookup_errors.append('user: %s' % user_status)

    raise click.ClickException(
        'Could not determine Girder resource type for %s. Tried: %s' % (
            parent_id, '; '.join(lookup_errors)))


def _list_http_error_summary(exc_info):
    """
    Return a short description of a Girder HTTP lookup failure.
    """
    response = exc_info.response
    status_code = getattr(response, 'status_code', None)
    reason = getattr(response, 'reason', '')
    if status_code is None:
        return str(exc_info)
    if reason:
        return '%s %s' % (status_code, reason)
    return str(status_code)


def _list_probe_user_resource(gc, user_id):
    """
    Return True if user_id appears to identify a user resource.

    A user record can be inaccessible while its public folders are still
    listable, so direct GET /user/<id> is not the only useful probe.
    """
    try:
        record = gc.get('user/%s' % user_id)
    except requests.HTTPError as exc_info:
        direct_status = _list_http_error_summary(exc_info)
        if exc_info.response.status_code not in {400, 403, 404}:
            raise
    else:
        if record:
            return True
        direct_status = 'empty response'

    try:
        records = gc.listFolder(user_id, parentFolderType='user', limit=1)
        first_record = next(iter(records), None)
    except requests.HTTPError as exc_info:
        if exc_info.response.status_code not in {400, 403, 404}:
            raise
        return 'GET user failed with %s; folder probe failed with %s' % (
            direct_status, _list_http_error_summary(exc_info))

    if first_record is not None:
        return True
    return 'GET user failed with %s; folder probe returned no folders' % direct_status


def _list_get_resource(gc, resource_type, resource_id):
    """
    Return a Girder record for a supported list resource type.

    GirderClient.getResource handles collections, folders, items, and files.
    User records are fetched through the user endpoint when possible. If the
    user record is not readable, return a minimal user-shaped record so the CLI
    can still show the requested opaque ID and list public folders below it.
    """
    if resource_type == 'user':
        try:
            record = gc.get('user/%s' % resource_id)
        except requests.HTTPError as exc_info:
            if exc_info.response.status_code in {400, 403, 404}:
                return {
                    '_id': resource_id,
                    '_modelType': 'user',
                }
            raise
        record.setdefault('_modelType', 'user')
        return record
    return gc.getResource(resource_type, resource_id)


def _list_record_label(record):
    """
    Return a compact label for a Girder record.
    """
    return record.get('name') or record.get('login') or record.get('_id')


def _list_record_info(gc, this_record, emitter):
    """
    Helper for :func:`_list` to print the requested record and its parents.
    """
    this_type = this_record.get('_modelType')
    if this_type == 'folder':
        prev_record = gc.getResource(this_record['parentCollection'], this_record['parentId'])
        if emitter:
            emitter.setitem('parent_record', prev_record)
        else:
            print('Parent {_modelType}: {_id} - {}'.format(
                _list_record_label(prev_record), **prev_record))
    elif this_type == 'item':
        prev_record = gc.getResource('folder', this_record['folderId'])
        if emitter:
            emitter.setitem('parent_record', prev_record)
        else:
            print('Parent {_modelType}: {_id} - {}'.format(
                _list_record_label(prev_record), **prev_record))
    elif this_type == 'file':
        item_record = gc.getResource('item', this_record['itemId'])
        folder_record = gc.getResource('folder', item_record['folderId'])
        if emitter:
            emitter.setitem('item_record', item_record)
            emitter.setitem('folder_record', folder_record)
        else:
            print('Parent folder: {_id} - {}'.format(
                _list_record_label(folder_record), **folder_record))
            print('Parent item: {_id} - {}'.format(
                _list_record_label(item_record), **item_record))
    elif this_type in {'collection', 'user'}:
        # Collections and users do not have a single parent record to show here.
        pass
    else:
        raise KeyError(this_type)

    if emitter:
        emitter.setitem('this_record', this_record)
    else:
        print('Listing {_modelType}: {_id} - {}'.format(
            _list_record_label(this_record), **this_record))


def _list_children_info(gc, parent_id, parent_type, child_types,
                        limit, offset, emitter):
    """
    Helper for :func:`_list` to print nested records.
    """
    import itertools
    for child_type in child_types:
        if child_type == 'folder':
            records = gc.listFolder(parent_id, limit=limit, offset=offset,
                                    parentFolderType=parent_type)
        elif child_type == 'item':
            records = gc.listItem(parent_id, limit=limit, offset=offset)
        elif child_type == 'file':
            records = gc.listFile(parent_id, limit=limit, offset=offset)
        else:
            raise NotImplementedError

        # Check if records has at least one element without losing it.
        records_copy, records = itertools.tee(records)
        first_records = list(itertools.islice(records_copy, 1))
        if first_records:
            if emitter:
                emitter.start_subcontainer(f'{child_type}_children')
                emitter.start_list()
            else:
                print('=== {} ==='.format(child_type))
                print('{:<24} {:<6} {:<24}'.format('ID', 'TYPE', 'NAME'))

        for record in records:
            if emitter:
                emitter.append(record)
            else:
                print('{_id:<24} {_modelType:<6} {}'.format(
                    _list_record_label(record), **record))

        if first_records and emitter:
            emitter.end_list()


if __name__ == '__main__':
    click.echo('Deprecation notice: Use "girder-client" to run the CLI.', err=True)
    main()
