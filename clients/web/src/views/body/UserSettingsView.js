import $                    from 'jquery';
import _                    from 'underscore';

import Auth                 from 'girder/auth';
import { AccessType }       from 'girder/constants';
import Events               from 'girder/events';
import EventStream          from 'girder/eventStream';
import Rest                 from 'girder/rest';
import router               from 'girder/router';
import UserModel            from 'girder/models/UserModel';
import UserSettingsTemplate from 'girder/templates/body/userSettings.jade';
import View                 from 'girder/view';

import 'bootstrap/js/tab';

/**
 * This is the view for the user account (profile) page.
 */
export var UserAccountView = View.extend({
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
                        Events.trigger('g:alert', {
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
                        Events.trigger('g:alert', {
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
        this.user = settings.user || Auth.getCurrentUser();
        this.isCurrentUser = Auth.getCurrentUser() &&
            settings.user.get('_id') === Auth.getCurrentUser().get('_id');

        this.model = this.user;
        this.temporary = settings.temporary;

        if (!this.user ||
                this.user.getAccessLevel() < AccessType.WRITE) {
            router.navigate('users', {trigger: true});
            return;
        }

        Rest.cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        if (Auth.getCurrentUser() === null) {
            router.navigate('users', {trigger: true});
            return;
        }

        this.$el.html(UserSettingsTemplate({
            user: this.model,
            isCurrentUser: this.isCurrentUser,
            Auth: Auth,
            temporaryToken: this.temporary
        }));

        _.each($('.g-account-tabs>li>a'), function (el) {
            var tabLink = $(el);
            var view = this;
            tabLink.tab().on('shown.bs.tab', function (e) {
                view.tab = $(e.currentTarget).attr('name');
                router.navigate('useraccount/' +
                    view.model.get('_id') + '/' + view.tab);
            });

            if (tabLink.attr('name') === this.tab) {
                tabLink.tab('show');
            }
        }, this);

        return this;
    }
});

router.route('useraccount/:id/:tab', 'accountTab', function (id, tab) {
    var user = new UserModel();
    user.set({
        _id: id
    }).on('g:fetched', function () {
        Events.trigger('g:navigateTo', UserAccountView, {
            user: user,
            tab: tab
        });
    }, this).on('g:error', function () {
        router.navigate('users', {trigger: true});
    }, this).fetch();
});

router.route('useraccount/:id/token/:token', 'accountToken', function (id, token) {
    Rest.restRequest({
        path: 'user/password/temporary/' + id,
        type: 'GET',
        data: {token: token},
        error: null
    }).done(_.bind(function (resp) {
        resp.user.token = resp.authToken.token;
        EventStream.close();
        Auth.setCurrentUser(new UserModel(resp.user));
        EventStream.open();
        Events.trigger('g:login-changed');
        Events.trigger('g:navigateTo', UserAccountView, {
            user: Auth.getCurrentUser(),
            tab: 'password',
            temporary: token
        });
    }, this)).error(_.bind(function () {
        router.navigate('users', {trigger: true});
    }, this));
});
