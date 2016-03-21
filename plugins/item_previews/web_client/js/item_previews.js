/**
 * The Item Preview widget shows a preview of items under a given folder.
 * For now, the only supported item previews are image previews.
 */

var MAX_JSON_SIZE = 2e6 /* bytes */;

var    _isSupportedItem = function (item) {
  return _isImageItem(item) || _isJSONItem(item);
};

var _isJSONItem = function (item) {
  return /\.(json)$/i.test(item.get('name'));
};

var _isImageItem = function (item) {
  return /\.(jpg|jpeg|png|gif)$/i.test(item.get('name'));
};


girder.views.ItemPreviewWidget = girder.View.extend({

  initialize: function (settings) {
    this.collection = new girder.collections.ItemCollection();

    this.collection.on('g:changed', function () {
      this.trigger('g:changed');
      this.render();
    }, this).fetch({
      folderId: settings.folderId
    });
  },

  events: {
    'click a.g-item-preview-link': function (event) {
      // TODO: trigger a 'g:itemClicked' based on cid
      // or other method rather than this lazy link proxy:
      var name = $(event.currentTarget).attr('g-item-name');
      $('.g-item-list a').filter(function(i, d) {
        return (name === $(d).text())
      }).click();
    },
  },

  render: function () {

    var supportedItems = this.collection.filter(_isSupportedItem);

    this.$el.html(girder.templates.itemPreviews({
      items: supportedItems,
      hasMore: this.collection.hasNextPage(),
      isImageItem: _isImageItem,
      isJSONItem: _isJSONItem,
      girder: girder,
    }));

    // Render any JSON files.
    supportedItems.filter(_isJSONItem).forEach(function (item) {
      var id = item.get('_id');

      // Don't process JSON files that are too big to preview.
      var size = item.get('size');
      if (size > MAX_JSON_SIZE) {
        return $('.json[data-id="' + id + '"]').text('JSON too big to preview.');
      }

      // Ajax request the JSON files to display them.
      var name = item.get('name');
      girder.restRequest({
        path: 'item/' + id + '/download',
        type: 'GET',
        error: null // don't do default error behavior (validation may fail)
      }).done(function (resp) {
        $('.json[data-id="' + id + '"]').text(JSON.stringify(resp, null, '\t'));
      }).error(function (err) {
        console.log('error',err);
      });
    })

    return this;
  }

});

girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {

  render.call(this);

  // Only on folder views:
  if (this.parentModel.resourceName === 'folder' && this._showItems) {

    // Add the item-previews-container.
    var element = $('<div class="g-item-previews-container">');
    this.$el.append(element);

    // Add the item preview widget into the container.
    this.itemPreviewView = new girder.views.ItemPreviewWidget({
      folderId: this.parentModel.get('_id'),
      parentView: this,
      el: element
    })
    .render();
  }

  return this;

});
