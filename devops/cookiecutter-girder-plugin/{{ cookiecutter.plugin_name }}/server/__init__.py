#!/usr/bin/env python
# -*- coding: utf-8 -*-
from girder import events, logger
from girder.utility.model_importer import ModelImporter
from .constants import PluginSettings
from .rest import {{ cookiecutter.plugin_camel_case }}
from .settings import defaultItemMetadata, validateItemMetadata  # noqa


# For more information on the events system, see:
# http://girder.readthedocs.io/en/latest/plugin-development.html#the-events-system
def addItemMeta(event):
    try:
        item = event.info
        item_metadata = ModelImporter.model('setting').get(PluginSettings.ITEM_METADATA)
        ModelImporter.model('item').setMetadata(item, {
            '{{ cookiecutter.plugin_name }}': item_metadata
        })
    except Exception:
        logger.warn('Failed to set metadata %s on item %s' % ('{{ cookiecutter.plugin_name }}',
                                                              str(item['_id'])))


# For more information on loading custom plugins, see:
# http://girder.readthedocs.io/en/latest/plugin-development.html#extending-the-server-side-application
def load(info):
    info['apiRoot'].{{ cookiecutter.plugin_name }} = {{ cookiecutter.plugin_camel_case }}()

    events.bind('model.item.save.after', 'add_{{ cookiecutter.plugin_name }}_item_meta', addItemMeta)
