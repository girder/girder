girder.models.GroupModel = girder.AccessControlledModel.extend({
    resourceName: 'group',

    /**
     * Send an invitation to this group to the user identified by userId.
     * Requires moderator (write) access on the group.
     * @param userId The ID of the user to invite.
     * @param accessType The access level to invite them as.
     * @param request Set to true if this is accepting a user's request to join.
     * @param [params] Additional parameters to pass with the request.
     */
    sendInvitation: function (userId, accessType, request, params) {
        params = params || {};
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/invitation',
            data: _.extend({
                userId: userId,
                level: accessType
            }, params),
            type: 'POST',
            error: null
        }).done(_.bind(function (resp) {
            this.set(resp);

            if (!request && userId === girder.currentUser.get('_id')) {
                if (params.force) {
                    girder.currentUser.addToGroup(this.get('_id'));
                } else {
                    girder.currentUser.addInvitation(this.get('_id'), accessType);
                }
            }
            this.trigger('g:invited');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Accept an invitation to join a group. Only call this if the user has
     * already been invited to the group.
     */
    joinGroup: function () {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/member',
            type: 'POST'
        }).done(_.bind(function (resp) {
            girder.currentUser.addToGroup(this.get('_id'));
            girder.currentUser.removeInvitation(this.get('_id'));

            this.set(resp);

            this.trigger('g:joined');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * This will create an invitation request on this group for the current
     * user. Requires read access on the group. If the user already has an
     * outstanding invitation to this group, call joinGroup instead.
     */
    requestInvitation: function () {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/member',
            type: 'POST'
        }).done(_.bind(function (resp) {
            this.set(resp);

            this.trigger('g:inviteRequested');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Promote a user to moderator or administrator. Requires admin access
     * on the group.
     * @param user The user model of the user being promoted
     * @param level The AccessLevel (WRITE or ADMIN) to promote to
     */
    promoteUser: function (user, level) {
        var role;
        if (level === girder.AccessType.WRITE) {
            role = 'moderator';
        } else if (level === girder.AccessType.ADMIN) {
            role = 'admin';
        }
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/' + role,
            data: {
                userId: user.get('_id')
            },
            type: 'POST'
        }).done(_.bind(function (resp) {
            this.set(resp);

            this.trigger('g:promoted');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Demote a user to ordinary member status. Requires admin access on the
     * group.
     * @param userId The id of the user to demote.
     * @param level The current access level of the user.
     */
    demoteUser: function (userId, level) {
        var role;
        if (level === girder.AccessType.WRITE) {
            role = 'moderator';
        } else if (level === girder.AccessType.ADMIN) {
            role = 'admin';
        }
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/' + role +
                '?userId=' + userId,
            type: 'DELETE'
        }).done(_.bind(function (resp) {
            this.set(resp);

            this.trigger('g:demoted');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Remove a member of a group, or if the user is not already a member,
     * this will simply delete any outstanding membership request or
     * invitation for this user.
     * @param userId The ID of the user to remove.
     */
    removeMember: function (userId) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') +
                  '/member?userId=' + userId,
            type: 'DELETE'
        }).done(_.bind(function (resp) {
            if (userId === girder.currentUser.get('_id')) {
                girder.currentUser.removeFromGroup(this.get('_id'));
            }

            this.set(resp);

            this.trigger('g:removed');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /* Check if the current user has the authority in this group to directly
     * add members.
     *
     * @returns: true if adding members is allowed.
     */
    mayAddMembers: function () {
        if (girder.currentUser.get('admin')) {
            return true;
        }
        var groupAddAllowed;
        var addToGroupPolicy = this.get('_addToGroupPolicy');
        if (addToGroupPolicy === 'nomod' || addToGroupPolicy === 'yesmod') {
            groupAddAllowed = 'mod';
        } else if (addToGroupPolicy === 'noadmin' || addToGroupPolicy === 'yesadmin') {
            groupAddAllowed = 'admin';
        } else {
            return false;
        }
        var addAllowed = this.get('addAllowed') || '';
        if (addAllowed === 'no' || (addToGroupPolicy.substr(0, 3) !== 'yes' &&
                addAllowed.substr(0, 3) !== 'yes')) {
            return false;
        }
        if (addAllowed === 'yesadmin') {
            groupAddAllowed = 'admin';
        }
        if (groupAddAllowed === 'admin' &&
                this.get('_accessLevel') >= girder.AccessType.ADMIN) {
            return true;
        }
        if (groupAddAllowed === 'mod' &&
                this.get('_accessLevel') >= girder.AccessType.WRITE) {
            return true;
        }
        return false;
    }
});
