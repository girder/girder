from pathlib import Path

from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.item import Item
from girder.models.setting import Setting
from girder.plugin import GirderPlugin, registerPluginStaticContent

from .rest import getLicenses
from .settings import PluginSettings


def validateString(value):
    """
    Make sure a value is a unicode string.

    :param value: the value to coerce into a unicode string if it isn't already.
    :returns: the unicode string version of the value.
    """
    if value is None:
        value = ''
    if not isinstance(value, str):
        value = str(value)
    return value


def updateItemLicense(event):
    """
    REST event handler to update item with license parameter, if provided.
    """
    params = event.info['params']
    if 'license' not in params:
        return

    itemModel = Item()
    item = itemModel.load(event.info['returnVal']['_id'], force=True, exc=True)
    newLicense = validateString(params['license'])
    if item['license'] == newLicense:
        return

    # Ensure that new license name is in configured list of licenses.
    #
    # Enforcing this here, instead of when validating the item, avoids an extra
    # database lookup (for the settings) on every future item save.
    if newLicense:
        licenseSetting = Setting().get(PluginSettings.LICENSES)
        validLicense = any(
            license['name'] == newLicense
            for group in licenseSetting
            for license in group['licenses'])
        if not validLicense:
            raise ValidationException(
                'License name must be in configured list of licenses.', 'license')

    item['license'] = newLicense
    item = itemModel.save(item)
    event.preventDefault()
    event.addResponse(item)


def postItemAfter(event):
    updateItemLicense(event)


def postItemCopyAfter(event):
    updateItemLicense(event)


def putItemAfter(event):
    updateItemLicense(event)


def validateItem(event):
    item = event.info
    item['license'] = validateString(item.get('license', None))


class ItemLicensesPlugin(GirderPlugin):
    DISPLAY_NAME = 'Item Licenses'

    def load(self, info):
        # Bind REST events
        events.bind('rest.post.item.after', 'item_licenses', postItemAfter)
        events.bind('rest.post.item/:id/copy.after', 'item_licenses', postItemCopyAfter)
        events.bind('rest.put.item/:id.after', 'item_licenses', putItemAfter)

        # Bind validation events
        events.bind('model.item.validate', 'item_licenses', validateItem)

        # Add license field to item model
        Item().exposeFields(level=AccessType.READ, fields='license')

        # Add endpoint to get list of licenses
        info['apiRoot'].item.route('GET', ('licenses',), getLicenses)

        registerPluginStaticContent(
            plugin='item_licenses',
            css=['/style.css'],
            js=['/girder-plugin-item-licenses.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
