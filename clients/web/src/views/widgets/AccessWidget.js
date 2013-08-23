/**
 * This view allows users to see and control access on a resource.
 */
girder.views.AccessWidget = Backbone.View.extend({
    events: {
        'click button.g-save-access-list': 'saveAccessList'
    },

    initialize: function (settings) {
        this.model = settings.model;
        this.modelType = settings.modelType;

        if (this.model.get('access')) {
            this.render();
        }
        else {
            this.model.on('g:accessFetched', function () {
                this.render();
            }, this).fetchAccess();
        }
    },

    render: function () {
        this.$el.html(jade.templates.accessList({
            model: this.model,
            modelType: this.modelType
        }));
        return this;
    },

    saveAccessList: function (event) {
        $(event.currentTarget).attr('disabled', 'disabled');

        // TODO build the access list from the UI, send
        // it up to the appropriate endpoint. In the case of
        // a folder, prompt for setting it recursively.
    }
});
