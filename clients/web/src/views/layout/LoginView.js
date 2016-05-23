import Auth                        from 'girder/auth';
import { handleClose, handleOpen } from 'girder/utilities/DialogHelper';
import Events                      from 'girder/events';
import LoginDialogTemplate         from 'girder/templates/layout/loginDialog.jade';
import View                        from 'girder/view';

import 'bootstrap/js/modal';
import 'girder/utilities/jQuery'; // $.girderModal

/**
 * This view shows a login modal dialog.
 */
export var LoginView = View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            Auth.login(this.$('#g-login').val(), this.$('#g-password').val());

            Events.once('g:login.success', function () {
                this.$el.modal('hide');
            }, this);

            Events.once('g:login.error', function (status, err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-login-button').removeClass('disabled');
            }, this);

            this.$('#g-login-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            Events.trigger('g:registerUi');
        },

        'click a.g-forgot-password': function () {
            Events.trigger('g:resetPasswordUi');
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
