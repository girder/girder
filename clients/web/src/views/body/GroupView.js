/**
 * This view shows a single group's page.
 */
girder.views.GroupView = Backbone.View.extend({
    events: {
        'click .g-edit-group': 'editGroup'
    },

    initialize: function (settings) {
        // If group model is already passed, there is no need to fetch.
        if (settings.group) {
            this.model = settings.group;
            console.log(this.model);

            this.isMember = false;
            this.isInvited = false;

            if (girder.currentUser) {
                _.every(girder.currentUser.get('groups'), function (groupId) {
                    if (groupId === this.model.get('_id')) {
                        this.isMember = true;
                        return false; // 'break;'
                    }
                    return true;
                }, this);

                _.every(girder.currentUser.get('groupInvites'), function (inv) {
                    if (inv['groupId'] === this.model.get('_id')) {
                        this.isInvited = true;
                        return false; // 'break;'
                    }
                    return true;
                }, this);
        }
            this.render();

            // This page should be re-rendered if the user logs in or out
            girder.events.on('g:login', this.userChanged, this);
        }
        else {
            console.error('Implement fetch then render group');
        }

    },

    editGroup: function () {
        var container = $('#g-dialog-container');

        if (!this.editGroupWidget) {
            this.editGroupWidget = new girder.views.EditGroupWidget({
                el: container,
                model: this.model
            }).off('g:saved').on('g:saved', function (group) {
                this.render();
            }, this);
        }
        this.editGroupWidget.render();
    },

    render: function () {
        this.$el.html(jade.templates.groupPage({
            group: this.model,
            girder: girder,
            isInvited: this.isInvited,
            isMember: this.isMember
        }));

        this.$('.g-group-actions-button').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        girder.router.navigate('group/' + this.model.get('_id'));

        return this;
    },

    userChanged: function () {
        // When the user changes, we should refresh the model to update the
        // _accessLevel attribute on the viewed group, then re-render the page.
        this.model.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).on('g:error', function () {
            // Current user no longer has read access to this user, so we
            // send them back to the user list page.
            girder.events.trigger('g:navigateTo',
                girder.views.GroupsView);
        }, this).fetch();
    }

});

girder.router.route('group/:id', 'group', function (id) {
    // Fetch the group by id, then render the view.
    var group = new girder.models.GroupModel();
    group.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.GroupView, {
            group: group
        }, group);
    }, this).on('g:error', function () {
        girder.events.trigger('g:navigateTo', girder.views.GroupsView);
    }, this).fetch();
});
