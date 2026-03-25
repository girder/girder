import UserModel from '@girder/core/models/UserModel';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { getCurrentUser, setCurrentUser, getCurrentToken, setCurrentToken } from '@girder/core/auth';
import { handleClose, handleOpen } from '@girder/core/dialog';

import RegisterDialogTemplate from '@girder/core/templates/layout/registerDialog.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var RegisterView = View.extend({
    events: {
        'submit #g-register-form': function (e) {
            e.preventDefault();

            this.$('.form-group').removeClass('has-error');

            if (this.$('#g-password').val() !== this.$('#g-password2').val()) {
                this.$('#g-group-password,#g-group-password2').addClass('has-error');
                this.$('#g-password').trigger('focus');
                this.$('.g-validation-failed-message').text('Passwords must match.');
                return;
            }

            var user = new UserModel({
                login: this.$('#g-login').val(),
                password: this.$('#g-password').val(),
                email: this.$('#g-email').val(),
                firstName: this.$('#g-firstName').val(),
                lastName: this.$('#g-lastName').val()
            });
            user.on('g:saved', function () {
                if (getCurrentUser()) {
                    this.trigger('g:userCreated', {
                        user: user
                    });
                } else {
                    var authToken = user.get('authToken') || {};

                    if (authToken.token) {
                        setCurrentUser(user);
                        setCurrentToken(authToken.token);
                        window.localStorage.setItem('girderToken', getCurrentToken());

                        events.trigger('g:login');
                    } else {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Check your email to verify registration.',
                            type: 'success',
                            timeout: 4000
                        });
                    }

                    handleClose('register', { replace: true });
                }

                this.$el.modal('hide');
            }, this).on('g:error', function (err) {
                var resp = err.responseJSON;
                this.$('.g-validation-failed-message').text(resp.message);
                if (resp.field) {
                    this.$('#g-group-' + resp.field).addClass('has-error');
                    this.$('#g-' + resp.field).trigger('focus');
                }
                this.$('#g-register-button').girderEnable(true);
            }, this).save();

            this.$('#g-register-button').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-login-link': function () {
            events.trigger('g:loginUi');
        }
    },

    render: function () {
        this.$el.html(RegisterDialogTemplate({
            currentUser: getCurrentUser(),
            title: getCurrentUser() ? 'Create new user' : 'Sign up'
        })).girderModal(this)
            .on('shown.bs.modal', () => {
                this.$('#g-login').trigger('focus');
            }).on('hidden.bs.modal', () => {
                handleClose('register', { replace: true });
            });
        this.$('#g-login').trigger('focus');

        handleOpen('register', { replace: true });

        return this;
    }

});

export default RegisterView;
