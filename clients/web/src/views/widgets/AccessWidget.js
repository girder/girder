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

        // Rebuild the access list
        var acList = {
            users: [],
            groups: []
        };

        _.each(this.$('.g-group-access-entry'), function (el) {
            var $el = $(el);
            acList.groups.push({
                name: $el.find('.g-desc-title').html(),
                id: $el.attr('groupid'),
                level: parseInt($el.find('.g-access-col-right>select').val())
            });
        }, this);

        _.each(this.$('.g-user-access-entry'), function (el) {
            var $el = $(el);
            acList.users.push({
                login: $el.find('.g-desc-subtitle').html(),
                name: $el.find('.g-desc-title').html(),
                id: $el.attr('userid'),
                level: parseInt($el.find('.g-access-col-right>select').val())
            });
        }, this);

        this.model.set({
            access: acList,
            public: this.$('#g-access-public').is(':checked')
        });

        this.model.off('g:accessListSaved')
                  .on('g:accessListSaved', function () {
            this.$el.modal('hide');
        }, this).updateAccess();
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
