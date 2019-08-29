import $ from 'jquery';

import GroupCollection from '@girder/core/collections/GroupCollection';
import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import router from '@girder/core/router';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

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
            router.navigate('plugins', { trigger: true });
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
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['autojoin'])
            }
        }).done((resp) => {
            this.rules = resp['autojoin'] || [];
            this.render();
        });
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

        return this;
    },

    _saveSettings: function (settings) {
        restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-autojoin-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
