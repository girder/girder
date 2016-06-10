girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {
    render.call(this);

    this.$('.g-folder-header-buttons').prepend(girder.templates.curation_button());
    this.$('.g-curation-button').tooltip({
        container: 'body',
        placement: 'auto',
        delay: 100
    });

    return this;
});

girder.views.HierarchyWidget.prototype.events['click .g-curation-button'] = function (e) {
    // console.log(this);
    new girder.views.curation_CurationDialog({
        el: $('#g-dialog-container'),
        parentView: this,
        folder: this.parentModel
    }).render();
};

girder.views.curation_CurationDialog = girder.View.extend({
    events: {
    },

    initialize: function (settings) {
    },

    render: function () {
        var folder = this.parentView.parentModel;
        this.$el.html(girder.templates.curation_dialog({
            folder: folder
        })).girderModal(this).on('shown.bs.modal', function () {
        });
        return this;
    }
});
