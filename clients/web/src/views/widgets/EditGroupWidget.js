var $            = require('jquery');
var girder       = require('girder/init');
var Auth         = require('girder/auth');
var GroupModel   = require('girder/models/GroupModel');
var DialogHelper = require('girder/utilities/DialogHelper');
var View         = require('girder/view');

/**
 * This widget is used to create a new group or edit an existing one.
 */
var EditGroupWidget = View.extend({
    events: {
        'submit #g-group-edit-form': function (e) {
            e.preventDefault();

            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val(),
                public: this.$('#g-access-public').is(':checked')
            };
            if (this.$('#g-add-to-group').length) {
                fields.addAllowed = this.$('#g-add-to-group').val();
            }

            if (this.model) {
                this.updateGroup(fields);
            } else {
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
        var pub = this.model ? this.model.get('public') : false;
        var groupAddAllowed;
        var addToGroupPolicy = this.model ? this.model.get('_addToGroupPolicy') : null;
        if (Auth.getCurrentUser().get('admin')) {
            if (addToGroupPolicy === 'nomod' || addToGroupPolicy === 'yesmod') {
                groupAddAllowed = 'mod';
            } else if (addToGroupPolicy === 'noadmin' || addToGroupPolicy === 'yesadmin') {
                groupAddAllowed = 'admin';
            }
        }
        var modal = this.$el.html(girder.templates.editGroupWidget({
            group: this.model,
            public: pub,
            addToGroupPolicy: addToGroupPolicy,
            groupAddAllowed: groupAddAllowed,
            addAllowed: this.model ? this.model.get('addAllowed') : false
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-name').focus();
            if (view.model) {
                DialogHelper.handleOpen('edit');
            } else {
                DialogHelper.handleOpen('create');
            }
        }).on('hidden.bs.modal', function () {
            if (view.create) {
                DialogHelper.handleClose('create');
            } else {
                DialogHelper.handleClose('edit');
            }
        }).on('ready.girder.modal', function () {
            if (view.model) {
                view.$('#g-name').val(view.model.get('name'));
                view.$('#g-description').val(view.model.get('description'));
                view.create = false;
            } else {
                view.create = true;
            }
        });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));
        this.$('#g-name').focus();

        this.privacyChanged();

        return this;
    },

    createGroup: function (fields) {
        var group = new GroupModel();
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

module.exports = EditGroupWidget;
