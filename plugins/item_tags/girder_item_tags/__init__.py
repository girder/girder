import re
from girder import plugin
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.exceptions import ValidationException
from girder.models.item import Item
from girder.models.setting import Setting
from girder.utility import search, setting_utilities

ITEM_TAG_LIST = 'item_tags.tag_list'


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'Item Tags'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].resource.route('GET', ('tags',), getItemTags)
        Item().ensureIndex(([('meta.girder_item_tags', 1)], {
            'collation': {
                'locale': 'en_US',
                'strength': 1
            }
        }))
        # Pytest reloads the plugin for every test.
        # addSearchMode will break if called twice, so check if it's already been loaded.
        if search.getSearchModeHandler('item_tags') is None:
            search.addSearchMode('item_tags', search_handler)


@setting_utilities.default(ITEM_TAG_LIST)
def _default_item_tag_list():
    return []


@setting_utilities.validator(ITEM_TAG_LIST)
def _validate_item_tag_list(tags):
    if type(tags['value']) != list:
        raise ValidationException('The setting is not a list', 'value')
    for index, tag in enumerate(tags['value']):
        if type(tag) != str:
            raise ValidationException(f'Tag {index} is not a string', 'value')


def search_handler(query, types, user=None, level=None, limit=0, offset=0):
    # Break the query into a list of keywords separated by whitespace
    query = re.compile(r'\W+').split(query.strip())
    # Find all items that are tagged with every string in the query
    cursor = Item()\
        .find({'meta.girder_item_tags': {'$all': query}})\
        .collation({'locale': 'en_US', 'strength': 1})
    # Filter the result
    result = {
        'item': [
            Item().filter(doc, user)
            for doc in Item().filterResultsByPermission(cursor, user, level, limit, offset)
        ]
    }

    return result


@access.public()
@autoDescribeRoute(
    Description('Get the list of valid item tags.')
    .errorResponse()
)
def getItemTags():
    return Setting().get(ITEM_TAG_LIST)
