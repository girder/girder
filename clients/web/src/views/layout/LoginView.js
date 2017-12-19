import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';
import { handleClose, handleOpen } from 'girder/dialog';
import { login } from 'girder/auth';
import { restRequest } from 'girder/rest';

import LoginDialogTemplate from 'girder/templates/layout/loginDialog.pug';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

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
                this.$('#g-login-button').girderEnable(true);
                if (err.responseJSON.extra === 'emailVerification') {
                    var html = err.responseJSON.message +
                        ' <a class="g-send-verification-email">Click here to send verification email.</a>';
                    $('.g-validation-failed-message').html(html);
                }
            }, this);

            this.$('#g-login-button').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        },

        'click .g-send-verification-email': function () {
            this.$('.g-validation-failed-message').html('');
            restRequest({
                url: 'user/verification',
                method: 'POST',
                data: {login: this.$('#g-login').val()},
                error: null
            }).done(_.bind(function (resp) {
                this.$('.g-validation-failed-message').html(resp.message);
            }, this)).fail(_.bind(function (err) {
                this.$('.g-validation-failed-message').html(err.responseJSON.message);
            }, this));
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
            enablePasswordLogin: this.enablePasswordLogin
        })).girderModal(this)
            .on('shown.bs.modal', () => {
                this.$('#g-login').focus();
            }).on('hidden.bs.modal', () => {
                handleClose('login', {replace: true});
            });

        handleOpen('login', {replace: true});
        this.$('#g-login').focus();

        return this;
    }
});

export default LoginView;
