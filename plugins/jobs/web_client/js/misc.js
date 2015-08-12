girder.models.JobModel = girder.AccessControlledModel.extend({
    resourceName: 'job'
});

girder.collections.JobCollection = girder.Collection.extend({
    resourceName: 'job',
    model: girder.models.JobModel
});

// The same job status enum as the server.
girder.jobs_JobStatus = {
    INACTIVE: 0,
    QUEUED: 1,
    RUNNING: 2,
    SUCCESS: 3,
    ERROR: 4,
    CANCELED: 5,

    _map: {
        0: {
            text: 'Inactive',
            icon: 'icon-pause'
        },
        1: {
            text: 'Queued',
            icon: 'icon-ellipsis'
        },
        2: {
            text: 'Running',
            icon: 'icon-spin3 animate-spin'
        },
        3: {
            text: 'Success',
            icon: 'icon-ok'
        },
        4: {
            text: 'Error',
            icon: 'icon-cancel'
        },
        5: {
            text: 'Canceled',
            icon: 'icon-cancel'
        }
    },

    text: function (status) {
        return this._map[status].text;
    },

    icon: function (status) {
        return this._map[status].icon;
    }
};

/**
 * Add an entry to the user dropdown menu to navigate to user's job list view.
 */
girder.wrap(girder.views.LayoutHeaderUserView, 'render', function (render) {
    render.call(this);

    if (girder.currentUser) {
        this.$('#g-user-action-menu>ul').prepend(girder.templates.jobs_userMenu({
            href: '#jobs/user/' + girder.currentUser.id
        }));
    }
    return this;
});
