/**
 * This view shows a login modal dialog.
 */
girder.views.LoginView = Backbone.View.extend({
    events: {
        'submit #g-login-form': function (e) {
            e.preventDefault();

            var authStr = btoa(this.$('#g-login').val() + ':' +
                               this.$('#g-password').val());
            girder.restRequest({
                path: 'user/authentication',
                type: 'GET',
                headers: {
                    'Authorization': 'Basic ' + authStr
                },
                error: null // don't do default error behavior
            }).done(_.bind(function (resp) {
                this.$el.modal('hide');

                // Save the token for later
                resp.user.token = resp.authToken.token;

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
        },

        'click a.g-forgot-password': function () {
            girder.events.trigger('g:resetPasswordUi');
        }
    },

    loadPlusButton: function () {
      var po = document.createElement('script');
      po.type = 'text/javascript';
      po.async = true;
      po.src = 'https://apis.google.com/js/client:plus.js?onload=girder.views.LoginView.showPlusButton';
      var s = document.getElementsByTagName('script')[0];
      s.parentNode.insertBefore(po, s);
    },

    showPlusButton: function () {
      var additionalParams = {
        'theme': 'dark',
        'clientid': '7097820446-3snot2finh14e1pvmq19s2tjupi0toto.apps.googleusercontent.com',
        'cookiepolicy': 'none',
        'requestvisbleactions': 'http://schemas.google.com/AddActivity',
        'scope': 'https://www.googleapis.com/auth/plus.login',
        'callback': this.plusSigninCallback
      };
      gapi.signin.render('myButton', additionalParams);
    },

    plusSigninCallback: function (authResult) {
      if (authResult['status']['signed_in']) {
        console.log(authResult);
        console.log("--before");
        var request = gapi.plus.people.get({
          'userId' : 'me'
        });

        request.execute(function(resp) {
          console.log(resp);
        });
        console.log("--after");

      } else {
        // Update the app to reflect a signed out user
        // Possible error values:
        //   "user_signed_out" - User is signed-out
        //   "access_denied" - User denied access to your app
        //   "immediate_failed" - Could not automatically log in the user
        console.log('Sign-in state: ' + authResult['error']);
      }
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.loginDialog())
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-login').focus();
            });
        this.$('#g-login').focus();

        this.loadPlusButton();

        return this;
    }
});
