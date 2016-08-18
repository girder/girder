/**
 * This view shows a register modal dialog.
 */
girder.views.RegisterView = girder.View.extend({
    events: {
        'submit #g-register-form': function (e) {
            e.preventDefault();

            this.$('.form-group').removeClass('has-error');

            if (this.$('#g-password').val() !== this.$('#g-password2').val()) {
                this.$('#g-group-password,#g-group-password2').addClass('has-error');
                this.$('#g-password').focus();
                this.$('.g-validation-failed-message').text('Passwords must match.');
                return;
            }

            var user = new girder.models.UserModel({
                login: this.$('#g-login').val(),
                password: this.$('#g-password').val(),
                email: this.$('#g-email').val(),
                firstName: this.$('#g-firstName').val(),
                lastName: this.$('#g-lastName').val()
            });
            user.on('g:saved', function () {
                if (girder.currentUser) {
                    this.trigger('g:userCreated', {
                        user: user
                    });
                } else {
                    var authToken = user.get('authToken') || {};

                    if (authToken.token) {
                        girder.currentUser = user;
                        girder.currentToken = authToken.token;

                        if (girder.corsAuth) {
                            document.cookie = 'girderToken=' + girder.currentToken;
                        }

                        girder.events.trigger('g:login');
                    } else {
                        girder.events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Check your email to verify registration.',
                            type: 'success',
                            timeout: 4000
                        });
                    }

                    girder.dialogs.handleClose('register', {replace: true});
                }

                this.$el.modal('hide');
            }, this).on('g:error', function (err) {
                var resp = err.responseJSON;
                this.$('.g-validation-failed-message').text(resp.message);
                if (resp.field) {
                    this.$('#g-group-' + resp.field).addClass('has-error');
                    this.$('#g-' + resp.field).focus();
                }
                this.$('#g-register-button').removeClass('disabled');
            }, this).save();

            this.$('#g-register-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-login-link': function () {
            girder.events.trigger('g:loginUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(girder.templates.registerDialog({
            currentUser: girder.currentUser,
            title: girder.currentUser ? 'Create new user' : 'Sign up'
        })).girderModal(this)
            .on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            }).on('hidden.bs.modal', function () {
                girder.dialogs.handleClose('register', {replace: true});
            });
        this.$('#g-login').focus();

        girder.dialogs.handleOpen('register', {replace: true});

        return this;
    }

});
