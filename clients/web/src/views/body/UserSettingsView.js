/**
 * This is the view for the user account (profile) page.
 */
girder.views.UserAccountView = girder.View.extend({
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
                        girder.events.trigger('g:alert', {
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
                        girder.events.trigger('g:alert', {
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
        this.user = settings.user || girder.currentUser;
        this.isCurrentUser = girder.currentUser &&
            settings.user.id === girder.currentUser.id;

        this.model = this.user;
        this.temporary = settings.temporary;

        if (!this.user || this.user.getAccessLevel() < girder.AccessType.WRITE) {
            girder.router.navigate('users', {trigger: true});
            return;
        }

        girder.cancelRestRequests('fetch');

        this.apiKeyListWidget = new girder.views.ApiKeyListWidget({
            user: this.user,
            parentView: this
        });

        this.render();
    },

    render: function () {
        if (girder.currentUser === null) {
            girder.router.navigate('users', {trigger: true});
            return;
        }

        this.$el.html(girder.templates.userSettings({
            user: this.model,
            isCurrentUser: this.isCurrentUser,
            girder: girder,
            temporaryToken: this.temporary
        }));

        _.each($('.g-account-tabs>li>a'), function (el) {
            var tabLink = $(el);
            tabLink.tab().on('shown.bs.tab', _.bind(function (e) {
                this.tab = $(e.currentTarget).attr('name');
                girder.router.navigate('useraccount/' + this.model.id + '/' + this.tab);

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
});

girder.router.route('useraccount/:id/:tab', 'accountTab', function (id, tab) {
    var user = new girder.models.UserModel();
    user.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.UserAccountView, {
            user: user,
            tab: tab
        });
    }, this).on('g:error', function () {
        girder.router.navigate('users', {trigger: true});
    }, this).fetch();
});

girder.router.route('useraccount/:id/token/:token', 'accountToken', function (id, token) {
    girder.restRequest({
        path: 'user/password/temporary/' + id,
        type: 'GET',
        data: {token: token},
        error: null
    }).done(_.bind(function (resp) {
        resp.user.token = resp.authToken.token;
        girder.eventStream.close();
        girder.currentUser = new girder.models.UserModel(resp.user);
        girder.eventStream.open();
        girder.events.trigger('g:login-changed');
        girder.events.trigger('g:navigateTo', girder.views.UserAccountView, {
            user: girder.currentUser,
            tab: 'password',
            temporary: token
        });
    }, this)).error(_.bind(function () {
        girder.router.navigate('users', {trigger: true});
    }, this));
});

girder.router.route('useraccount/:id/verify/:token', 'accountVerify', function (id, token) {
    girder.restRequest({
        path: 'user/verify/' + id,
        type: 'GET',
        data: {token: token},
        error: null
    }).done(_.bind(function (resp) {
        resp.user.token = resp.authToken.token;
        girder.eventStream.close();
        girder.currentUser = new girder.models.UserModel(resp.user);
        girder.eventStream.open();
        girder.events.trigger('g:login-changed');
        girder.events.trigger('g:navigateTo', girder.views.FrontPageView);
        girder.events.trigger('g:alert', {
            icon: 'ok',
            text: 'Email verified.',
            type: 'success',
            timeout: 4000
        });
    }, this)).error(_.bind(function () {
        girder.router.navigate('users', {trigger: true});
    }, this));
});
