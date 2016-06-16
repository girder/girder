function _addCurationButton() {
    $('.g-folder-actions-menu').append(girder.templates.curation_button());
}

// add curation button to hiearchy widget
girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.get('_modelType') === 'folder') {
        // add button if an admin or if curation is enabled
        if (girder.currentUser.get('admin')) {
            _addCurationButton();
        } else {
            girder.restRequest({
                path: 'folder/' + this.parentModel.get('_id') + '/curation'
            }).done(_.bind(function (resp) {
                if (resp.enabled) {
                    _addCurationButton();
                }
            }, this));
        }
    }

    return this;
});

// launch modal when curation button is clicked
girder.views.HierarchyWidget.prototype.events['click .g-curation-button'] = function (e) {
    new girder.views.CurationDialog({
        el: $('#g-dialog-container'),
        parentView: this,
        folder: this.parentModel
    }).render();
};

// curation dialog
girder.views.CurationDialog = girder.View.extend({
    events: {
        'click #g-curation-enable': function (event) {
            event.preventDefault();
            this._save('Enabled folder curation', {
                id: this.folder.get('_id'),
                enabled: true
            });
        },
        'click #g-curation-disable': function (event) {
            event.preventDefault();
            this._save('Disabled folder curation', {
                id: this.folder.get('_id'),
                enabled: false
            });
        },
        'click #g-curation-request': function (event) {
            event.preventDefault();
            this._save('Submitted folder for admin approval', {
                id: this.folder.get('_id'),
                status: 'requested'
            });
        },
        'click #g-curation-approve': function (event) {
            event.preventDefault();
            this._save('Approved curated folder', {
                id: this.folder.get('_id'),
                status: 'approved'
            });
        },
        'click #g-curation-reject': function (event) {
            event.preventDefault();
            this._save('Rejected curated folder', {
                id: this.folder.get('_id'),
                status: 'construction'
            });
        },
        'click #g-curation-reopen': function (event) {
            event.preventDefault();
            this._save('Reopened curated folder', {
                id: this.folder.get('_id'),
                status: 'construction'
            });
        }
    },

    initialize: function (settings) {
        this.folder = this.parentView.parentModel;
        this.curation = {timeline: []};
        girder.restRequest({
            path: 'folder/' + this.folder.get('_id') + '/curation'
        }).done(_.bind(function (resp) {
            this.curation = resp;
            this.render();
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.curation_dialog({
            folder: this.folder,
            curation: this.curation,
            moment: window.moment
        })).girderModal(this);

        // show only relevant action buttons
        $('.g-curation-action-container button').hide();
        if (this.curation.enabled) {
            if (this.curation.status === 'construction') {
                $('#g-curation-request').show();
            }
            if (girder.currentUser.get('admin')) {
                $('#g-curation-disable').show();
                if (this.curation.status === 'requested') {
                    $('#g-curation-approve').show();
                    $('#g-curation-reject').show();
                }
                if (this.curation.status === 'approved') {
                    $('#g-curation-reopen').show();
                }
            }
        } else {
            if (girder.currentUser.get('admin')) {
                $('#g-curation-enable').show();
            }
        }

        return this;
    },

    _save: function (successText, data) {
        girder.restRequest({
            type: 'PUT',
            path: 'folder/' + this.folder.get('_id') + '/curation',
            data: data
        }).done(_.bind(function () {
            this.$el.modal('hide');
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: successText,
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-curation-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});
