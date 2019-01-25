import _ from 'underscore';

import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import { AccessType } from '@girder/core/constants';
import { getCurrentUser } from '@girder/core/auth';
import { restRequest } from '@girder/core/rest';

var GroupModel = AccessControlledModel.extend({
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
        return restRequest({
            url: `${this.resourceName}/${this.id}/invitation`,
            data: _.extend({
                userId: userId,
                level: accessType
            }, params),
            method: 'POST',
            error: null
        }).done((resp) => {
            this.set(resp);

            if (!request && userId === getCurrentUser().get('_id')) {
                if (params.force) {
                    getCurrentUser().addToGroup(this.get('_id'));
                } else {
                    getCurrentUser().addInvitation(this.get('_id'), accessType);
                }
            }
            this.trigger('g:invited');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Accept an invitation to join a group. Only call this if the user has
     * already been invited to the group.
     */
    joinGroup: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/member`,
            method: 'POST'
        }).done((resp) => {
            getCurrentUser().addToGroup(this.get('_id'));
            getCurrentUser().removeInvitation(this.get('_id'));

            this.set(resp);

            this.trigger('g:joined');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * This will create an invitation request on this group for the current
     * user. Requires read access on the group. If the user already has an
     * outstanding invitation to this group, call joinGroup instead.
     */
    requestInvitation: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/member`,
            method: 'POST'
        }).done((resp) => {
            this.set(resp);

            this.trigger('g:inviteRequested');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Promote a user to moderator or administrator. Requires admin access
     * on the group.
     * @param user The user model of the user being promoted
     * @param level The AccessLevel (WRITE or ADMIN) to promote to
     */
    promoteUser: function (user, level) {
        var role;
        if (level === AccessType.WRITE) {
            role = 'moderator';
        } else if (level === AccessType.ADMIN) {
            role = 'admin';
        }
        return restRequest({
            url: `${this.resourceName}/${this.id}/${role}`,
            data: {
                userId: user.get('_id')
            },
            method: 'POST'
        }).done((resp) => {
            this.set(resp);

            this.trigger('g:promoted');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Demote a user to ordinary member status. Requires admin access on the
     * group.
     * @param userId The id of the user to demote.
     * @param level The current access level of the user.
     */
    demoteUser: function (userId, level) {
        var role;
        if (level === AccessType.WRITE) {
            role = 'moderator';
        } else if (level === AccessType.ADMIN) {
            role = 'admin';
        }
        return restRequest({
            url: `${this.resourceName}/${this.id}/${role}?userId=${userId}`,
            method: 'DELETE'
        }).done((resp) => {
            this.set(resp);

            this.trigger('g:demoted');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Remove a member of a group, or if the user is not already a member,
     * this will simply delete any outstanding membership request or
     * invitation for this user.
     * @param userId The ID of the user to remove.
     */
    removeMember: function (userId) {
        return restRequest({
            url: `${this.resourceName}/${this.id}/member?userId=${userId}`,
            method: 'DELETE'
        }).done((resp) => {
            if (userId === getCurrentUser().get('_id')) {
                getCurrentUser().removeFromGroup(this.get('_id'));
            }

            this.set(resp);

            this.trigger('g:removed');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /* Check if the current user has the authority in this group to directly
     * add members.
     *
     * @returns: true if adding members is allowed.
     */
    mayAddMembers: function () {
        if (getCurrentUser().get('admin')) {
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
                this.get('_accessLevel') >= AccessType.ADMIN) {
            return true;
        }
        if (groupAddAllowed === 'mod' &&
                this.get('_accessLevel') >= AccessType.WRITE) {
            return true;
        }
        return false;
    }
});

export default GroupModel;
