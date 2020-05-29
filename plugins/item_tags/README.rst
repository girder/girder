=========
Item Tags
=========

Searchable keyword tags for items.

Features
--------

- Tag any item with any number of keyword tags.
- Search for items with a given set of tags using a new custom search mode.
- Configure a list of allowed tags in the plugin settings.

Item tags are stored in the item metadata.
Although they can be modified there, it is recommended to only use the included Tag widget.

The search mode `Item tag search` must be select for tags to be searched.
Searches are case insensitive and will only apply to tags, not to titles or descriptions.
An item must be tagged with every word in a search query to be included in the search results;
The search `"foo bar"` will only match items that are tagged with both `foo` and `bar`.

Only tags in the allowed tag list can be apllied to items.
Modifying or deleting items from the allowed tag list will not modify or delete those tags from items that already have them.
If an item is tagged with `foo` and the `foo` tag is edited to be `bar`, the item will still be tagged with `foo`.
However, it will not be possible to save any changes to the item's tags until the tag `foo` is removed from the item.
