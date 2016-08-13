girder.views.autojoin_ConfigView = girder.View.extend({
    events: {
        'click .g-autojoin-remove': function (event) {
            this.$('#g-autojoin-error-message').text('');
            var index = parseInt($(event.currentTarget).attr('data-index'));
            this.rules.splice(index, 1);
            this.render();
        },
        'click #g-autojoin-add': function (event) {
            this.$('#g-autojoin-error-message').text('');
            var pattern = $('#g-autojoin-pattern').val();
            var group = $('#g-autojoin-group').val();
            var level = $('#g-autojoin-level').val();
            if (pattern === '' || group === '' || level === '') {
                this.$('#g-autojoin-error-message').text(
                    'All fields are required.');
                return;
            }
            var rule = {
                pattern: pattern,
                groupId: group,
                level: parseInt(level),
            };
            this.rules.push(rule);
            this.render();
        },
        'click #g-autojoin-save': function (event) {
            this.$('#g-autojoin-error-message').text('');
            this._saveSettings([{
                key: 'autojoin',
                value: this.rules
            }]);
        },
        'click #g-autojoin-cancel': function (event) {
            girder.router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function () {
        this.rules = [];

        this.collection = new girder.collections.GroupCollection();
        this.collection.pageLimit = 0;
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['autojoin'])
            }
        }).done(_.bind(function (resp) {
            this.rules = resp['autojoin'] || [];
            this.render();
        }, this));
    },

    render: function () {
        var groups = this.collection.toArray();

        var groupsById = {};
        groups.forEach(function (group) {
            groupsById[group.get('_id')] = group;
        });

        var levelNames = {
            0: 'Member',
            1: 'Moderator',
            2: 'Admin'
        };

        this.$el.html(girder.templates.autojoin_config({
            rules: this.rules,
            groups: groups,
            groupsById: groupsById,
            levelNames: levelNames
        }));

        new girder.views.PluginConfigBreadcrumbWidget({
            pluginName: 'Auto Join',
            el: this.$('.g-config-breadcrumb-container'),
            parentView: this
        }).render();

        this.$('[title]').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    },

    _saveSettings: function (settings) {
        girder.restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-autojoin-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }

});

girder.router.route('plugins/autojoin/config', 'autojoinConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.autojoin_ConfigView);
});
