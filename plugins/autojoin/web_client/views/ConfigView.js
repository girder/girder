import _ from 'underscore';

import GroupCollection from 'girder/collections/GroupCollection';
import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import router from 'girder/router';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'click .g-autojoin-remove': function (event) {
            this.$('#g-autojoin-error-message').text('');
            var index = parseInt($(event.currentTarget).attr('data-index'), 10);
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
                level: parseInt(level, 10)
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
            router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function () {
        this.rules = [];

        this.collection = new GroupCollection();
        this.collection.pageLimit = 0;
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        restRequest({
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

        this.$el.html(ConfigViewTemplate({
            rules: this.rules,
            groups: groups,
            groupsById: groupsById,
            levelNames: levelNames
        }));

        new PluginConfigBreadcrumbWidget({
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
        restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            events.trigger('g:alert', {
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

export default ConfigView;
