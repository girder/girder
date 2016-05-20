var LayoutHeaderTemplate = require('girder/templates/layout/layoutHeader.jade');
var LayoutHeaderUserView = require('girder/views/layout/HeaderUserView');
var Router               = require('girder/router');
var SearchFieldWidget    = require('girder/views/widgets/SearchFieldWidget');
var View                 = require('girder/view');

/**
 * This view shows the header in the layout.
 */
var LayoutHeaderView = View.extend({
    events: {
        'click .g-app-title': function () {
            Router.navigate('', {trigger: true});
        }
    },

    initialize: function () {
        this.userView = new LayoutHeaderUserView({
            parentView: this
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Quick search...',
            types: ['item', 'folder', 'group', 'collection', 'user'],
            parentView: this
        }).on('g:resultClicked', function (result) {
            this.searchWidget.resetState();
            Router.navigate(result.type + '/' + result.id, {
                trigger: true
            });
        }, this);
    },

    render: function () {
        this.$el.html(LayoutHeaderTemplate());

        this.userView.setElement(this.$('.g-current-user-wrapper')).render();
        this.searchWidget.setElement(this.$('.g-quick-search-container')).render();
    }
});

module.exports = LayoutHeaderView;
