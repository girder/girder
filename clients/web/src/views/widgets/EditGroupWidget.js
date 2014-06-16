/**
 * This widget is used to create a new group or edit an existing one.
 */
girder.views.EditGroupWidget = girder.View.extend({
    events: {
        'submit #g-group-edit-form': function (e) {
            e.preventDefault();

            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val(),
                public: this.$('#g-access-public').is(':checked')
            };

            if (this.model) {
                this.updateGroup(fields);
            }
            else {
                this.createGroup(fields);
            }

            this.$('button.g-save-group').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'change .g-public-container .radio input': 'privacyChanged'
    },

    initialize: function (settings) {
        this.model = settings.model || null;
    },

    render: function () {
        var view = this;
        var public = this.model ? this.model.get('public') : false;
        this.$el.html(jade.templates.editGroupWidget({
            group: this.model,
            public: public
        })).girderModal(this).on('shown.bs.modal', function () {
            if (view.model) {
                view.$('#g-name').val(view.model.get('name'));
                view.$('#g-description').val(view.model.get('description'));
            }
            view.$('#g-name').focus();
            girder.dialogs.handleOpen('edit');
        }).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('edit');
        });
        this.$('#g-name').focus();

        this.privacyChanged();

        return this;
    },

    createGroup: function (fields) {
        var group = new girder.models.GroupModel();
        group.set(fields);
        group.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', group);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-group').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    updateGroup: function (fields) {
        this.model.set(fields);
        this.model.off().on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-group').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    privacyChanged: function () {
        this.$('.g-public-container .radio').removeClass('g-selected');
        var selected = this.$('.g-public-container .radio input:checked');
        selected.parents('.radio').addClass('g-selected');
    }
});
