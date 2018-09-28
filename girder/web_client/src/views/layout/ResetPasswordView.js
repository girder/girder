import View from 'girder/views/View';
import events from 'girder/events';
import { handleClose, handleOpen } from 'girder/dialog';
import { restRequest } from 'girder/rest';

import ResetPasswordDialogTemplate from 'girder/templates/layout/resetPasswordDialog.pug';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

/**
 * This view shows a modal dialog for resetting a forgotten password.
 */
var ResetPasswordView = View.extend({
    events: {
        'submit #g-reset-password-form': function (e) {
            e.preventDefault();
            restRequest({
                url: 'user/password/temporary',
                data: {
                    email: this.$('#g-email').val().trim()
                },
                method: 'PUT',
                error: null // don't do default error behavior
            }).done(() => {
                this.$el.modal('hide');
                events.trigger('g:alert', {
                    icon: 'mail-alt',
                    text: 'Password reset email sent.',
                    type: 'success'
                });
            }).fail((err) => {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-reset-password-button').girderEnable(true);
            });

            this.$('#g-reset-password-button').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            events.trigger('g:registerUi');
        },

        'click a.g-login-link': function () {
            events.trigger('g:loginUi');
        }
    },

    initialize: function (settings) {
        this.registrationPolicy = settings.registrationPolicy;
    },

    render: function () {
        this.$el.html(ResetPasswordDialogTemplate({
            registrationPolicy: this.registrationPolicy
        })).girderModal(this).on('shown.bs.modal', () => {
            this.$('#g-email').focus();
        }).on('hidden.bs.modal', () => {
            handleClose('resetpassword', {replace: true});
        });
        this.$('#g-email').focus();

        handleOpen('resetpassword', {replace: true});

        return this;
    }
});

export default ResetPasswordView;
