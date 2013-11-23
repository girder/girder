/**
 * This view shows a register modal dialog.
 */
girder.views.RegisterView = Backbone.View.extend({
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
            girder.restRequest({
                path: 'user',
                type: 'POST',
                data: {
                    login: this.$('#g-login').val(),
                    password: this.$('#g-password').val(),
                    email: this.$('#g-email').val(),
                    firstName: this.$('#g-firstName').val(),
                    lastName: this.$('#g-lastName').val()
                },
                error: null // don't do default error behavior
            }).done(_.bind(function (user) {
                this.$el.modal('hide');

                girder.currentUser = new girder.models.UserModel(user);
                girder.events.trigger('g:login');
            }, this)).error(_.bind(function (err) {
                var resp = err.responseJSON;
                this.$('.g-validation-failed-message').text(resp.message);
                if (resp.field) {
                    this.$('#g-group-' + resp.field).addClass('has-error');
                    this.$('#g-' + resp.field).focus();
                }
                this.$('#g-register-button').removeClass('disabled');
            }, this));

            this.$('#g-register-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-login-link': function () {
            girder.events.trigger('g:loginUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.registerDialog())
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            });
        this.$('#g-login').focus();

        return this;
    }
});
