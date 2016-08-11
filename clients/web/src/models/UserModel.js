import _ from 'underscore';

import { fetchCurrentUser } from 'girder/auth';
import Model from 'girder/models/Model';
import { restRequest } from 'girder/rest';

var UserModel = Model.extend({
    resourceName: 'user',

    /**
     * Calling this function mutates the model in one of two ways: (1) if a user
     * is currently logged into Girder, the model will reflect that user; (2) if
     * no user is logged in, the model will become clear.  To know which path
     * occurred, you can call this method, then install a one-time event handler
     * for the model's change event.  In that handler, calling isNew() on the
     * model will tell if you if a user is logged in (false) or not (true).
     *
     * This is equivalent to invoking fetchCurrentUser(), then calling
     * clear() or set() on the model depending on whether the result of the call
     * is null or not.
     */
    current: function () {
        fetchCurrentUser()
            .then(_.bind(function (user) {
                if (user) {
                    this.set(user);
                } else {
                    this.clear();
                }
            }, this));
    },

    name: function () {
        return this.get('firstName') + ' ' + this.get('lastName');
    },

    /**
     * When this user is added to a group, call this on the user model.
     */
    addToGroup: function (groupId) {
        var groups = this.get('groups') || [];
        groups.push(groupId);
        this.set('groups', groups);
    },

    /**
     * When this user is removed from a group, call this on the user model.
     */
    removeFromGroup: function (groupId) {
        var groups = this.get('groups') || [];
        var index = groups.indexOf(groupId);

        while (index >= 0) {
            groups.splice(index, 1);
            index = groups.indexOf(groupId);
        }

        this.set('groups', groups);
    },

    /**
     * When this user is invited to a group, call this on the user model.
     */
    addInvitation: function (groupId, level) {
        var invites = this.get('groupInvites') || [];
        invites.push({
            groupId: groupId,
            level: level
        });

        this.set('groupInvites', invites);
    },

    /**
     * When this user's invitation is deleted, either by joining the group or
     * having the invitation deleted manually, this should be called on the user
     * model.
     */
    removeInvitation: function (groupId) {
        var invites = this.get('groupInvites') || [];
        var filtered = _.reject(invites, _.matcher({groupId: groupId}));

        this.set('groupInvites', filtered);
    },

    /**
     * Change the password for this user.
     */
    changePassword: function (oldPassword, newPassword) {
        return restRequest({
            path: this.resourceName + '/password',
            data: {
                old: oldPassword,
                new: newPassword
            },
            type: 'PUT',
            error: null
        }).done(_.bind(function () {
            this.trigger('g:passwordChanged');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Change the password for another user (as an admin).
     */
    adminChangePassword: function (newPassword) {
        return restRequest({
            path: this.resourceName + '/' + this.id + '/password',
            data: {
                password: newPassword
            },
            type: 'PUT',
            error: null
        }).done(_.bind(function () {
            this.trigger('g:passwordChanged');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});

export default UserModel;

