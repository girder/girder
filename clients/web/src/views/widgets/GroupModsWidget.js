var $                    = require('jquery');
var _                    = require('underscore');

var Constants            = require('girder/constants');
var Events               = require('girder/events');
var GroupModListTemplate = require('girder/templates/widgets/groupModList.jade');
var MiscFunctions        = require('girder/utilities/MiscFunctions');
var UserModel            = require('girder/models/UserModel');
var UserView             = require('girder/views/body/UserView');
var View                 = require('girder/view');

require('bootstrap/js/tooltip');

/**
 * This view shows a list of moderators of a group.
 */
var GroupModsWidget = View.extend({
    events: {
        'click .g-group-mod-promote': function (e) {
            var userid = $(e.currentTarget).parents('li').attr('userid');
            var user = new UserModel({_id: userid});
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, Constants.AccessType.ADMIN);
        },

        'click .g-group-mod-demote': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            MiscFunctions.confirm({
                text: 'Are you sure you want to remove moderator privileges ' +
                    'from <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-group-mod-remove': function (e) {
            var view = this;
            var li = $(e.currentTarget).parents('li');

            MiscFunctions.confirm({
                text: 'Are you sure you want to remove <b> ' +
                    _.escape(li.attr('username')) +
                    '</b> from this group?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.trigger('g:removeMember', li.attr('userid'));
                }
            });
        },

        'click a.g-member-name': function (e) {
            Events.trigger('g:navigateTo', UserView, {
                id: $(e.currentTarget).parents('li').attr('userid')
            });
        }
    },

    initialize: function (settings) {
        this.model = settings.group;
        this.moderators = settings.moderators;
    },

    render: function () {
        this.$el.html(GroupModListTemplate({
            group: this.model,
            level: this.model.get('_accessLevel'),
            moderators: this.moderators,
            accessType: Constants.AccessType
        }));

        this.$('.g-group-mod-demote.g-group-mod-promote,.g-group-mod-remove').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});

module.exports = GroupModsWidget;

