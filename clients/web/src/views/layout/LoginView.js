/**
 * This view shows a login modal dialog.
 */
girder.views.LoginView = girder.View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            girder.login(this.$('#g-login').val(), this.$('#g-password').val());

            girder.events.once('g:login.success', function () {
                this.$el.modal('hide');
            }, this);

            girder.events.once('g:login.error', function (status, err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-login-button').removeClass('disabled');
            }, this);

            this.$('#g-login-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            girder.events.trigger('g:registerUi');
        },

        'click a.g-forgot-password': function () {
            girder.events.trigger('g:resetPasswordUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(girder.templates.loginDialog()).girderModal(this)
            .on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            }).on('hidden.bs.modal', function () {
                girder.dialogs.handleClose('login', {replace: true});
            });

        girder.dialogs.handleOpen('login', {replace: true});
        this.$('#g-login').focus();

        return this;
    }

});
