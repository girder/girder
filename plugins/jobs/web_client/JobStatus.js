import _ from 'underscore';

// The same job status enum as the server.
var JobStatus = {
    _map: {},

    text: function (status) {
        var text = status;
        if (status in this._map) {
            text = this._map[status].text;
        }

        return '' + text;
    },

    icon: function (status) {
        var icon;
        if (status in this._map) {
            icon = this._map[status].icon;
        }

        return icon;
    },

    color: function (status) {
        return this._map[status].color;
    },

    /**
     * Convert this status text into a value appropriate for an HTML class name.
     */
    classAffix: function (status) {
        return this.text(status).toLowerCase().replace(/ /g, '-');
    },

    /**
     * Add new job statuses. The argument should be an object mapping the enum
     * symbol name to an information object for that status. The info object
     * must include a "value" field (its integer value), a "text" field, which
     * is how the status should be rendered as text, and an "icon" field for
     * what classes to apply to the icon for this status.
     */
    registerStatus: function (status) {
        _.each(status, function (info, name) {
            this[name] = info.value;
            this._map[info.value] = {
                text: info.text,
                icon: info.icon,
                color: info.color
            };
        }, this);
    },

    getAll: function () {
        return _.values(this._map);
    }
};

JobStatus.registerStatus({
    INACTIVE: {
        value: 0,
        text: 'Inactive',
        icon: 'icon-pause',
        color: '#ccc'
    },
    QUEUED: {
        value: 1,
        text: 'Queued',
        icon: 'icon-ellipsis',
        color: '#dbc345'
    },
    RUNNING: {
        value: 2,
        text: 'Running',
        icon: 'icon-spin3 animate-spin',
        color: '#6666d5'
    },
    SUCCESS: {
        value: 3,
        text: 'Success',
        icon: 'icon-ok',
        color: '#53b653'
    },
    ERROR: {
        value: 4,
        text: 'Error',
        icon: 'icon-cancel',
        color: '#d44'
    },
    CANCELED: {
        value: 5,
        text: 'Canceled',
        icon: 'icon-cancel',
        color: '#545'
    }
});

export default JobStatus;
