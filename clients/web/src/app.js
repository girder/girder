girder.App = Backbone.View.extend({
    el: 'body',

    initialize: function (settings) {
        "use strict";
        girder.restRequest({
            path: 'user/me'
        }).done(_.bind(function (user) {
            if (user) {
                girder.currentUser = new girder.models.UserModel(user);
            }
            this.render();
        }, this));

        Backbone.history.start({
            pushState: false,
            root: settings.root
        });

        girder.events.on('g:navigateTo', this.navigateTo, this);
        girder.events.on('g:loginUi', this.loginDialog, this);
        girder.events.on('g:registerUi', this.registerDialog, this);
    },

    render: function () {
        "use strict";
        this.$el.html(jade.templates.layout());

        new girder.views.LayoutGlobalNavView({
            el: this.$('#g-global-nav-container')
        }).render();

        new girder.views.LayoutHeaderView({
            el: this.$('#g-app-header-container')
        }).render();

        new girder.views.LayoutFooterView({
            el: this.$('#g-app-footer-container')
        }).render();

        return this;
    },

    /**
     * Changes the current body view to the view class specified by view.
     * @param view The view to display in the body.
     * @param [settings={}] Settings to pass to the view initialize() method.
     */
    navigateTo: function (view, settings) {
        "use strict";
        var container = this.$('#g-app-body-container');

        settings = settings || {};

        if (view) {
            // Unbind all events added by the previous occupant of this container.
            container.off();

            settings = _.extend(settings, {
                el: this.$('#g-app-body-container')
            });
            /* We let the view be created in this way even though it is
             * normally against convention.
             */
            /*jshint -W055 */
            this.bodyView = new view(settings);

            // TODO trigger router.navigate()
        }
        else {
            console.error('Undefined page.');
        }
        return this;
    },

    /**
     * Show a dialog allowing a user to login or register.
     */
    loginDialog: function () {
        "use strict";
        if (!this.loginView) {
            this.loginView = new girder.views.LoginView({
                el: this.$('#g-dialog-container')
            });
        }
        this.loginView.render();
    },

    registerDialog: function () {
        "use strict";
        if (!this.registerView) {
            this.registerView = new girder.views.RegisterView({
                el: this.$('#g-dialog-container')
            });
        }
        this.registerView.render();
    }
});
