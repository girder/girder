/**
 * This view allows users to see and control access on a resource.
 */
girder.views.AccessWidget = Backbone.View.extend({
    events: {
        'click button.g-save-access-list': 'saveAccessList',
        'click a.g-action-remove-access': 'removeAccessEntry',
        'change .g-public-container .radio input': 'privacyChanged'
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
        this.$el.html(jade.templates.accessEditor({
            model: this.model,
            modelType: this.modelType,
            accessList: this.model.get('access'),
            public: this.model.get('public'),
            accessTypes: girder.AccessType
        })).girderModal(this);

        this.$('.g-action-remove-access').tooltip({
            container: '.modal',
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });

        this.privacyChanged();

        return this;
    },

    saveAccessList: function (event) {
        $(event.currentTarget).attr('disabled', 'disabled');

        // TODO build the access list from the UI, send
        // it up to the appropriate endpoint. In the case of
        // a folder, prompt for setting it recursively.
    },

    removeAccessEntry: function (event) {
        var sel = '.g-user-access-entry,.g-group-access-entry';
        $(event.currentTarget).tooltip('hide').parents(sel).remove();
    },

    privacyChanged: function () {
        this.$('.g-public-container .radio').removeClass('g-selected');
        var selected = this.$('.g-public-container .radio input:checked');
        selected.parents('.radio').addClass('g-selected');
    }
});
