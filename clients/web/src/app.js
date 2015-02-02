girder.App = girder.View.extend({
    initialize: function (settings) {
        girder.restRequest({
            path: 'user/me'
        }).done(_.bind(function (user) {
            girder.eventStream = new girder.EventStream();

            this.headerView = new girder.views.LayoutHeaderView({
                parentView: this
            });

            this.globalNavView = new girder.views.LayoutGlobalNavView({
                parentView: this
            });

            this.footerView = new girder.views.LayoutFooterView({
                parentView: this
            });

            this.progressListView = new girder.views.ProgressListView({
                eventStream: girder.eventStream,
                parentView: this
            });

            if (user) {
                girder.currentUser = new girder.models.UserModel(user);
                girder.eventStream.open();
            }
            this.render();

            // Once we've rendered the layout, we can start up the routing.
            Backbone.history.start({
                pushState: false
            });
        }, this));

        girder.events.on('g:navigateTo', this.navigateTo, this);
        girder.events.on('g:loginUi', this.loginDialog, this);
        girder.events.on('g:registerUi', this.registerDialog, this);
        girder.events.on('g:resetPasswordUi', this.resetPasswordDialog, this);
        girder.events.on('g:alert', this.alert, this);
        girder.events.on('g:login', this.login, this);
    },

    render: function () {
        this.$el.html(girder.templates.layout());

        this.globalNavView.setElement(this.$('#g-global-nav-container')).render();
        this.headerView.setElement(this.$('#g-app-header-container')).render();
        this.footerView.setElement(this.$('#g-app-footer-container')).render();
        this.progressListView.setElement(this.$('#g-app-progress-container')).render();

        return this;
    },

    /**
     * Changes the current body view to the view class specified by view.
     * @param view The view to display in the body.
     * @param [settings={}] Settings to pass to the view initialize() method.
     */
    navigateTo: function (view, settings) {
        var container = this.$('#g-app-body-container');

        this.globalNavView.deactivateAll();

        settings = settings || {};

        if (view) {
            if (this.bodyView) {
                this.bodyView.destroy();
            }

            settings = _.extend(settings, {
                el: this.$('#g-app-body-container'),
                parentView: this
            });

            /* We let the view be created in this way even though it is
             * normally against convention.
             */
            /*jshint -W055 */
            // jscs:disable requireCapitalizedConstructors
            this.bodyView = new view(settings);
            // jscs:enable requireCapitalizedConstructors
        } else {
            console.error('Undefined page.');
        }
        return this;
    },

    /**
     * Close any open dialog if we are already logged in.
     * :returns: true if we have a current user.
     */
    closeDialogIfUser: function () {
        if (girder.currentUser) {
            $('.modal').girderModal('close');
            return true;
        }
        return false;
    },

    /**
     * Show a dialog allowing a user to login or register.
     */
    loginDialog: function () {
        if (this.closeDialogIfUser()) {
            return;
        }
        if (!this.loginView) {
            this.loginView = new girder.views.LoginView({
                el: this.$('#g-dialog-container'),
                parentView: this
            });
        }
        this.loginView.render();
    },

    registerDialog: function () {
        if (this.closeDialogIfUser()) {
            return;
        }
        if (!this.registerView) {
            this.registerView = new girder.views.RegisterView({
                el: this.$('#g-dialog-container'),
                parentView: this
            });
        }
        this.registerView.render();
    },

    resetPasswordDialog: function () {
        if (this.closeDialogIfUser()) {
            return;
        }
        if (!this.resetPasswordView) {
            this.resetPasswordView = new girder.views.ResetPasswordView({
                el: this.$('#g-dialog-container'),
                parentView: this
            });
        }
        this.resetPasswordView.render();
    },

    /**
     * Display a brief alert on the screen with the following options:
     *   - text: The text to be displayed
     *   - [type]: The alert class ('info', 'warning', 'success', 'danger').
     *             Default is 'info'.
     *   - [icon]: An optional icon to display in the alert.
     *   - [timeout]: How long before the alert should automatically disappear.
     *                Default is 6000ms. Set to <= 0 to have no timeout.
     */
    alert: function (options) {
        var el = $(girder.templates.alert({
            text: options.text,
            type: options.type || 'info',
            icon: options.icon
        }));
        $('#g-alerts-container').append(el);
        el.fadeIn(500);

        if (options.timeout === undefined) {
            options.timeout = 6000;
        }
        if (options.timeout > 0) {
            window.setTimeout(function () {
                el.fadeOut(750, function () {
                    $(this).remove();
                });
            }, options.timeout);
        }
    },

    /**
     * On login or logout, we re-render the current body view.
     */
    login: function () {
        var route = girder.dialogs.splitRoute(Backbone.history.fragment).base;
        Backbone.history.fragment = null;
        girder.router.navigate(route, {trigger: true});

        if (girder.currentUser) {
            girder.eventStream.close();
            girder.eventStream.open();
        } else {
            girder.eventStream.close();
        }
    }
});
