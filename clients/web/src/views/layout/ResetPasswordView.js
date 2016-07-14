/**
 * This view shows a modal dialog for resetting a forgotten password.
 */
girder.views.ResetPasswordView = girder.View.extend({
    events: {
        'submit #g-reset-password-form': function (e) {
            e.preventDefault();
            girder.restRequest({
                path: 'user/password/temporary',
                data: {
                    email: this.$('#g-email').val().trim()
                },
                type: 'PUT',
                error: null // don't do default error behavior
            }).done(_.bind(function () {
                this.$el.modal('hide');
                girder.events.trigger('g:alert', {
                    icon: 'mail-alt',
                    text: 'Password reset email sent.',
                    type: 'success'
                });
            }, this)).error(_.bind(function (err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-reset-password-button').removeClass('disabled');
            }, this));

            this.$('#g-reset-password-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            girder.events.trigger('g:registerUi');
        },

        'click a.g-login-link': function () {
            girder.events.trigger('g:loginUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(girder.templates.resetPasswordDialog(
        )).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-email').focus();
        }).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('resetpassword', {replace: true});
        });
        this.$('#g-email').focus();

        girder.dialogs.handleOpen('resetpassword', {replace: true});

        return this;
    }
});
