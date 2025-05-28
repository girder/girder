from pathlib import Path

from girder import plugin

from .rest import getImport, listAllImports, listImports, moveFolder


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'import_tracker'

    def load(self, info):
        plugin.getPlugin('jobs').load(info)

        info['apiRoot'].assetstore.route('GET', (':id', 'imports'), listImports)
        info['apiRoot'].assetstore.route('GET', ('all_imports',), listAllImports)
        info['apiRoot'].assetstore.route('GET', ('import', ':id'), getImport)

        info['apiRoot'].assetstore.importData.description.param(
            'excludeExisting',
            'If true, then a file with an import path that is already in the '
            'system is not imported, even if it is not in the destination '
            'hierarchy.', dataType='boolean', required=False, default=False
        )

        info['apiRoot'].folder.route('PUT', (':id', 'move'), moveFolder)

        plugin.registerPluginStaticContent(
            plugin='import-tracker',
            css=['style.css'],
            js=['girder-plugin-import-tracker.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot']
        )
