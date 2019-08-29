import $ from 'jquery';
import _ from 'underscore';

import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { handleClose, handleOpen } from '@girder/core/dialog';
import { login } from '@girder/core/auth';
import UserModel from '@girder/core/models/UserModel';

import LoginDialogTemplate from '@girder/core/templates/layout/loginDialog.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a login modal dialog.
 */
var LoginView = View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            this.$('#g-login-button').girderEnable(false);
            this.$('.g-validation-failed-message').text('');

            const loginName = this.$('#g-login').val();
            const password = this.$('#g-password').val();
            const otpToken = this.$('#g-login-otp-group').hasClass('hidden') ? null : this.$('#g-login-otp').val();
            login(loginName, password, undefined, otpToken)
                .done(() => {
                    this.$el.modal('hide');
                })
                .fail((err) => {
                    if (err.responseJSON.message.indexOf('Girder-OTP') !== -1 &&
                        this.$('#g-login-otp-group').hasClass('hidden')
                    ) {
                        this.$('#g-login-otp-group').removeClass('hidden');
                        this.$('#g-login-otp').focus();
                        return;
                    }

                    this.$('.g-validation-failed-message').text(err.responseJSON.message);

                    if (err.responseJSON.extra === 'emailVerification') {
                        var html = err.responseJSON.message +
                            ' <a class="g-send-verification-email">Click here to send verification email.</a>';
                        $('.g-validation-failed-message').html(html);
                    }
                })
                .always(() => {
                    this.$('#g-login-button').girderEnable(true);
                });
        },

        'click .g-send-verification-email': function () {
            this.$('.g-validation-failed-message').html('');

            const loginName = this.$('#g-login').val();
            UserModel.sendVerificationEmail(loginName)
                .done((resp) => {
                    this.$('.g-validation-failed-message').html(resp.message);
                }).fail((err) => {
                    this.$('.g-validation-failed-message').html(err.responseJSON.message);
                });
        },

        'click a.g-register-link': function () {
            events.trigger('g:registerUi');
        },

        'click a.g-forgot-password': function () {
            events.trigger('g:resetPasswordUi');
        }
    },

    initialize: function (settings) {
        this.registrationPolicy = settings.registrationPolicy;
        this.enablePasswordLogin = _.has(settings, 'enablePasswordLogin') ? settings.enablePasswordLogin : true;
    },

    render: function () {
        this.$el.html(LoginDialogTemplate({
            registrationPolicy: this.registrationPolicy,
            enablePasswordLogin: this.enablePasswordLogin,
            showOtp: true
        })).girderModal(this)
            .on('shown.bs.modal', () => {
                this.$('#g-login').focus();
            }).on('hidden.bs.modal', () => {
                handleClose('login', { replace: true });
            });

        handleOpen('login', { replace: true });
        this.$('#g-login').focus();

        return this;
    }
});

export default LoginView;
