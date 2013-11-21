/**
 * This view shows a login modal dialog.
 */
girder.views.LoginView = Backbone.View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            girder.restRequest({
                path: 'user/login',
                type: 'POST',
                data: {
                    login: this.$('#g-login').val(),
                    password: this.$('#g-password').val()
                },
                error: null // don't do default error behavior
            }).done(_.bind(function (resp) {
                this.$el.modal('hide');

                girder.currentUser = new girder.models.UserModel(resp.user);
                girder.events.trigger('g:login');
            }, this)).error(_.bind(function (err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('#g-login-button').removeClass('disabled');
            }, this));

            this.$('#g-login-button').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'click a.g-register-link': function () {
            girder.events.trigger('g:registerUi');
        }
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.loginDialog())
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            });
        this.$('#g-login').focus();

        return this;
    }
});
