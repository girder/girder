girder.models.UserModel = girder.Model.extend({
    resourceName: 'user',

    // Sets this model to the currently logged in user; has no effect is no user
    // is logged in.
    current: function (success, error) {
        girder.restRequest({
            method: "GET",
            path: "/user/me"
        }).then(_.bind(function (user) {
            if (user) {
                this.set(user);
                if (success) {
                    success(this);
                }
            } else {
                if (error) {
                    error(this);
                }
            }
        }, this));
    },

    // Attempts to log a user in, modifying the model to reflect that user if
    // successful; has no effect otherwise.
    login: function (username, password, success, error) {
        var auth = "Basic " + window.btoa(username + ":" + password),
            successC,
            errorC;

        successC = _.bind(function (resp) {
            this.set(resp.user);
            if (success) {
                success(this);
            }
        }, this);

        errorC = _.bind(function (resp) {
            if (error) {
                error(this, resp);
            }
        }, this);

        girder.restRequest({
            method: "GET",
            path: "/user/authentication",
            headers: {
                Authorization: auth
            }
        }).then(successC, errorC);
    },

    // Log out the currently logged in user.  On success, clears the model.
    logout: function (success, error) {
        var successC,
            errorC;

        successC = _.bind(function () {
            this.clear();
            if (success) {
                success(this);
            }
        }, this);

        errorC = _.bind(function (resp) {
            if (error) {
                error(this, resp);
            }
        }, this);

        girder.restRequest({
            method: "DELETE",
            path: "/user/authentication"
        }).then(successC, errorC);
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
        var filtered = [];

        _.each(invites, function (invite) {
            if (invite.groupId !== groupId) {
                filtered.push(invite);
            }
        }, this);

        this.set('groupInvites', filtered);
    },

    /**
     * Change the password for this user.
     */
    changePassword: function (oldPassword, newPassword) {
        girder.restRequest({
            path: this.resourceName + '/password',
            data: {
                old: oldPassword,
                new: newPassword
            },
            type: 'PUT',
            error: null
        }).done(_.bind(function (resp) {
            this.trigger('g:passwordChanged');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});
