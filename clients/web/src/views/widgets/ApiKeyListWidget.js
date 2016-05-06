girder.views.ApiKeyListWidget = girder.View.extend({
    events: {
        'click .g-api-key-toggle-active': function (e) {
            var apiKey = this._getModelFromEvent(e);
            var toggleActive = _.bind(function () {
                apiKey.setActive(!apiKey.get('active')).once('g:setActive', function () {
                    this.render();
                }, this);
            }, this);

            if (apiKey.get('active')) {
                girder.confirm({
                    text: 'Deactivating this API key will delete any existing tokens ' +
                          'created with it, and will not be usable until it is activated ' +
                          'again. Are you sure you want to deactivate it?',
                    yesText: 'Yes',
                    yesClass: 'btn-warning',
                    escapedHtml: true,
                    confirmCallback: toggleActive
                });
            } else {
                toggleActive();
            }
        },

        'click .g-api-key-new': function (e) {
            this._renderEditWidget();
        },

        'click .g-api-key-edit': function (e) {
            var apiKey = this._getModelFromEvent(e);
            this._renderEditWidget(apiKey);
        },

        'click .g-api-key-delete': function (e) {
            var apiKey = this._getModelFromEvent(e);

            girder.confirm({
                text: 'Are you sure you want to delete the API key <b>' +
                      apiKey.escape('name') + '</b>? Any client applications using ' +
                      'this key will no longer be able to authenticate.',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    apiKey.destroy().on('g:deleted', function () {
                        girder.events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'API key deleted.',
                            type: 'success',
                            timeout: 3000
                        });
                        this.render();
                    }, this);
                }, this)
            });
        }
    },

    /**
     * A widget for listing and editing API keys for a user.
     *
     * @param settings.user {girder.models.UserModel} The user whose keys to show.
     */
    initialize: function (settings) {
        this.model = settings.user;
        this.fetched = false;

        this.collection = new girder.collections.ApiKeyCollection();
        this.collection.on('g:changed', function () {
            this.fetched = true;
            this.render();
            this.trigger('g:changed');
        }, this).fetch({
            userId: this.model.id
        });

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.collection,
            parentView: this
        });
    },

    render: function () {
        if (!this.fetched) {
            return;
        }

        this.$el.html(girder.templates.apiKeyList({
            apiKeys: this.collection.toArray(),
            moment: window.moment
        }));

        this.$('button').tooltip();
        this.$('.g-show-api-key').popover({
            container: this.$('.g-api-key-table'),
            placement: 'top'
        });

        this.paginateWidget.setElement(this.$('.g-paginate-container')).render();

        return this;
    },

    _getModelFromEvent: function (e) {
        var cid = $(e.currentTarget).parents('.g-api-key-container').attr('cid');
        return this.collection.get(cid);
    },

    _renderEditWidget: function (apiKey) {
        if (!this.editApiKeyWidget) {
            this.editApiKeyWidget = new girder.views.EditApiKeyWidget({
                el: $('#g-dialog-container'),
                parentView: this
            }).on('g:saved', function (model) {
                if (!this.collection.get(model.cid)) {
                    this.collection.add(model);
                }
                this.render();
            }, this);
        }
        this.editApiKeyWidget.model = apiKey || null;
        this.editApiKeyWidget.render();
    }
});
