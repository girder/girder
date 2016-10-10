import $ from 'jquery';
import _ from 'underscore';

import ApiKeyListWidget from 'girder/views/widgets/ApiKeyListWidget';
import router from 'girder/router';
import UserModel from 'girder/models/UserModel';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import events from 'girder/events';
import eventStream from 'girder/utilities/EventStream';
import { getCurrentUser, setCurrentUser } from 'girder/auth';
import { restRequest, cancelRestRequests } from 'girder/rest';

import UserAccountTemplate from 'girder/templates/body/userAccount.pug';

import 'girder/stylesheets/body/userAccount.styl';

import 'bootstrap/js/tab';

/**
 * This is the view for the user account (profile) page.
 */
var UserAccountView = View.extend({
    events: {
        'submit #g-user-info-form': function (event) {
            event.preventDefault();
            this.$('#g-user-info-error-msg').empty();

            var params = {
                email: this.$('#g-email').val(),
                firstName: this.$('#g-firstName').val(),
                lastName: this.$('#g-lastName').val()
            };

            if (this.$('#g-admin').length > 0) {
                params.admin = this.$('#g-admin').is(':checked');
            }

            this.user.set(params);

            this.user.off('g:error').on('g:error', function (err) {
                var msg = err.responseJSON.message;
                this.$('#g-' + err.responseJSON.field).focus();
                this.$('#g-user-info-error-msg').text(msg);
            }, this).off('g:saved')
                    .on('g:saved', function () {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Info saved.',
                            type: 'success',
                            timeout: 4000
                        });
                    }, this).save();
        },
        'submit #g-password-change-form': function (event) {
            event.preventDefault();
            this.$('#g-password-change-error-msg').empty();

            if (this.$('#g-password-new').val() !==
                    this.$('#g-password-retype').val()) {
                this.$('#g-password-change-error-msg').text(
                    'Passwords do not match, try again.'
                );
                this.$('#g-password-retype,#g-password-new').val('');
                this.$('#g-password-new').focus();
                return;
            }

            this.user.off('g:error').on('g:error', function (err) {
                var msg = err.responseJSON.message;
                this.$('#g-password-change-error-msg').text(msg);
            }, this).off('g:passwordChanged')
                    .on('g:passwordChanged', function () {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Password changed.',
                            type: 'success',
                            timeout: 4000
                        });
                        this.$('#g-password-old,#g-password-new,#g-password-retype').val('');
                    }, this);

            // here and in the template, an admin user who wants to change their
            //   own password is intentionally forced to re-enter their old
            //   password
            if (this.isCurrentUser) {
                this.user.changePassword(
                    this.$('#g-password-old').val(),
                    this.$('#g-password-new').val()
                );
            } else {
                this.user.adminChangePassword(this.$('#g-password-new').val());
            }
        }
    },

    initialize: function (settings) {
        this.tab = settings.tab || 'info';
        this.user = settings.user || getCurrentUser();
        this.isCurrentUser = getCurrentUser() &&
            settings.user.id === getCurrentUser().id;

        this.model = this.user;
        this.temporary = settings.temporary;

        if (!this.user || this.user.getAccessLevel() < AccessType.WRITE) {
            router.navigate('users', {trigger: true});
            return;
        }

        cancelRestRequests('fetch');

        this.apiKeyListWidget = new ApiKeyListWidget({
            user: this.user,
            parentView: this
        });

        this.render();
    },

    render: function () {
        if (getCurrentUser() === null) {
            router.navigate('users', {trigger: true});
            return;
        }

        this.$el.html(UserAccountTemplate({
            user: this.model,
            isCurrentUser: this.isCurrentUser,
            getCurrentUser: getCurrentUser,
            temporaryToken: this.temporary
        }));

        _.each($('.g-account-tabs>li>a'), function (el) {
            var tabLink = $(el);
            tabLink.tab().on('shown.bs.tab', _.bind(function (e) {
                this.tab = $(e.currentTarget).attr('name');
                router.navigate('useraccount/' + this.model.id + '/' + this.tab);

                if (this.tab === 'apikeys') {
                    this.apiKeyListWidget.setElement(
                        this.$('.g-api-keys-list-container')).render();
                }
            }, this));

            if (tabLink.attr('name') === this.tab) {
                tabLink.tab('show');
            }
        }, this);

        return this;
    }
}, {
    /**
     * Helper function for fetching the user by id, then render the view.
     */
    fetchAndInit: function (id, tab) {
        var user = new UserModel();
        user.set({ _id: id }).on('g:fetched', function () {
            events.trigger('g:navigateTo', UserAccountView, {
                user: user,
                tab: tab
            });
        }, this).on('g:error', function () {
            router.navigate('users', {trigger: true});
        }, this).fetch();
    },

    temporaryPassword: function (id, token) {
        restRequest({
            path: 'user/password/temporary/' + id,
            type: 'GET',
            data: {token: token},
            error: null
        }).done(_.bind(function (resp) {
            resp.user.token = resp.authToken.token;
            eventStream.close();
            setCurrentUser(new UserModel(resp.user));
            eventStream.open();
            events.trigger('g:login-changed');
            events.trigger('g:navigateTo', UserAccountView, {
                user: getCurrentUser(),
                tab: 'password',
                temporary: token
            });
        }, this)).error(_.bind(function () {
            router.navigate('users', {trigger: true});
        }, this));
    }
});

export default UserAccountView;
