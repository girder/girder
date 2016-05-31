import { login } from 'girder/auth';
import { handleClose, handleOpen } from 'girder/utilities/DialogHelper';
import { events } from 'girder/events';
import View from 'girder/views/View';

import LoginDialogTemplate from 'girder/templates/layout/loginDialog.jade';

import 'bootstrap/js/modal';
import 'girder/utilities/jQuery'; // $.girderModal

/**
 * This view shows a login modal dialog.
 */
var LoginView = View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            login(this.$('#g-login').val(), this.$('#g-password').val());

            events.once('g:login.success', function () {
                this.$el.modal('hide');
            }, this);

            events.once('g:login.error', function (status, err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-login-button').removeClass('disabled');
            }, this);

            this.$('#g-login-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            events.trigger('g:registerUi');
        },

        'click a.g-forgot-password': function () {
            events.trigger('g:resetPasswordUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(LoginDialogTemplate()).girderModal(this)
            .on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            }).on('hidden.bs.modal', function () {
                handleClose('login', {replace: true});
            });

        handleOpen('login', {replace: true});
        this.$('#g-login').focus();

        return this;
    }
});

export default LoginView;
