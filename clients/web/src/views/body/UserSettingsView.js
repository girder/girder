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
                    'Passwords do not match, try again.');
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
            }, this).changePassword(
                this.$('#g-password-old').val(),
                this.$('#g-password-new').val());
        }
    },

    initialize: function (settings) {
        this.tab = settings.tab || 'info';
        this.user = settings.user || girder.currentUser;
        this.isCurrentUser = girder.currentUser &&
            settings.user.get('_id') === girder.currentUser.get('_id');

        this.model = this.user;

        if (!this.user ||
            this.user.getAccessLevel() < girder.AccessType.WRITE) {
            girder.router.navigate('users', {trigger: true});
            return;
        }

        this.render();

        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.userChanged, this);
    },

    render: function () {

        if (girder.currentUser === null) {
            girder.router.navigate('users', {trigger: true});
            return;
        }

        this.$el.html(jade.templates.userSettings({
            user: this.model,
            girder: girder
        }));

        _.each($('.g-account-tabs>li>a'), function (el) {
            var tabLink = $(el);
            var view = this;
            tabLink.tab().on('shown.bs.tab', function (e) {
                view.tab = $(e.currentTarget).attr('name');
                girder.router.navigate('useraccount/' +
                    view.model.get('_id') + '/' + view.tab);
            });

            if (tabLink.attr('name') === this.tab) {
                tabLink.tab('show');
            }
        }, this);

        return this;
    },

    userChanged: function () {
        // When the user changes, we should refresh the model to update the
        // _accessLevel attribute on the viewed user, then re-render the page.
        this.model.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).on('g:error', function () {
            // Current user no longer has write access to this user, so we
            // send them back to the user list page.
            girder.router.navigate('users', {trigger: true});
        }, this).fetch();
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
