import $                   from 'jquery';
import _                   from 'underscore';
import Backbone            from 'backbone';

import AlertTemplate       from 'girder/templates/layout/alert.jade';
import Auth                from 'girder/auth';
import { Layout }          from 'girder/constants';
import { splitRoute }      from 'girder/utilities/DialogHelper';
import Events              from 'girder/events';
import EventStream         from 'girder/eventStream';
import LayoutFooterView    from 'girder/views/layout/FooterView';
import LayoutGlobalNavView from 'girder/views/layout/GlobalNavView';
import LayoutHeaderView    from 'girder/views/layout/HeaderView';
import LayoutTemplate      from 'girder/templates/layout/layout.jade';
import LoginView           from 'girder/views/layout/LoginView';
import ProgressListView    from 'girder/views/layout/ProgressListView';
import RegisterView        from 'girder/views/layout/RegisterView';
import ResetPasswordView   from 'girder/views/layout/ResetPasswordView';
import router              from 'girder/router';
import UserModel           from 'girder/models/UserModel';
import View                from 'girder/view';

import 'girder/utilities/jQuery'; // $.girderModal

export var App = View.extend({
    initialize: function () {
        Auth.fetchCurrentUser()
            .done(_.bind(function (user) {
                this.headerView = new LayoutHeaderView({
                    parentView: this
                });

                this.globalNavView = new LayoutGlobalNavView({
                    parentView: this
                });

                this.footerView = new LayoutFooterView({
                    parentView: this
                });

                this.progressListView = new ProgressListView({
                    eventStream: EventStream,
                    parentView: this
                });

                if (user) {
                    Auth.setCurrentUser(new UserModel(user));
                    EventStream.open();
                }

                this.layoutRenderMap = {};
                this.layoutRenderMap[Layout.DEFAULT] = this._defaultLayout;
                this.layoutRenderMap[Layout.EMPTY] = this._emptyLayout;
                this.render();

                // Once we've rendered the layout, we can start up the routing.
                Backbone.history.start({
                    pushState: false
                });
            }, this));

        Events.on('g:navigateTo', this.navigateTo, this);
        Events.on('g:loginUi', this.loginDialog, this);
        Events.on('g:registerUi', this.registerDialog, this);
        Events.on('g:resetPasswordUi', this.resetPasswordDialog, this);
        Events.on('g:alert', this.alert, this);
        Events.on('g:login', this.login, this);
    },

    _layout: 'default',

    _defaultLayout: {
        show: function () {
            this.$('#g-app-header-container,#g-global-nav-container,#g-app-footer-container').show();
            this.$('#g-app-body-container').addClass('g-default-layout');
        },

        hide: function () {
            this.$('#g-app-header-container,#g-global-nav-container,#g-app-footer-container').hide();
            this.$('#g-app-body-container').removeClass('g-default-layout');
        }
    },

    _emptyLayout: {
        show: function () {
            this.$('#g-app-body-container').addClass('g-empty-layout');
        },

        hide: function () {
            this.$('#g-app-body-container').removeClass('g-empty-layout');
        }
    },

    render: function () {
        this.$el.html(LayoutTemplate());

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
     * @param opts Additional options for navigateTo, if any.
     */
    navigateTo: function (view, settings, opts) {
        this.globalNavView.deactivateAll();

        settings = settings || {};
        opts = opts || {};

        if (opts.layout) {
            if (this._layout !== opts.layout) {
                if (_.has(this.layoutRenderMap, opts.layout)) {
                    // set a layout if opts specifies one different from current
                    this.layoutRenderMap[this._layout].hide.call(this, opts);
                    this._layout = opts.layout;
                    this.layoutRenderMap[this._layout].show.call(this, opts);
                } else {
                    console.error('Attempting to set unknown layout type: ' + opts.layout);
                }
            }
        } else if (this._layout !== Layout.DEFAULT) {
            // reset to default as needed when nothing specified in opts
            this.layoutRenderMap[this._layout].hide.call(this, opts);
            this._layout = Layout.DEFAULT;
            this.layoutRenderMap[this._layout].show.call(this, opts);
        }

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
            this.bodyView = new view(settings); // eslint-disable-line new-cap
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
        if (Auth.getCurrentUser()) {
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
            this.loginView = new LoginView({
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
            this.registerView = new RegisterView({
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
            this.resetPasswordView = new ResetPasswordView({
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
        var el = $(AlertTemplate({
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
     * On login we re-render the current body view; whereas on
     * logout, we redirect to the front page.
     */
    login: function () {
        var route = splitRoute(Backbone.history.fragment).base;
        Backbone.history.fragment = null;
        EventStream.close();

        if (Auth.getCurrentUser()) {
            EventStream.open();
            router.navigate(route, {trigger: true});
        } else {
            router.navigate('/', {trigger: true});
        }
    }
});
