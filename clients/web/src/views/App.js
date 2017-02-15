import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import events from 'girder/events';
import eventStream from 'girder/utilities/EventStream';
import LayoutFooterView from 'girder/views/layout/FooterView';
import LayoutGlobalNavView from 'girder/views/layout/GlobalNavView';
import LayoutHeaderView from 'girder/views/layout/HeaderView';
import LoginView from 'girder/views/layout/LoginView';
import ProgressListView from 'girder/views/layout/ProgressListView';
import RegisterView from 'girder/views/layout/RegisterView';
import ResetPasswordView from 'girder/views/layout/ResetPasswordView';
import router from 'girder/router';
import UserModel from 'girder/models/UserModel';
import View from 'girder/views/View';
import { fetchCurrentUser, setCurrentUser, getCurrentUser } from 'girder/auth';
import { Layout } from 'girder/constants';
import { splitRoute } from 'girder/misc';

import AlertTemplate from 'girder/templates/layout/alert.pug';
import LayoutTemplate from 'girder/templates/layout/layout.pug';

import 'girder/routes';

import 'girder/stylesheets/layout/global.styl';
import 'girder/stylesheets/layout/layout.styl';

import 'girder/utilities/jquery/girderModal';

import 'bootstrap/dist/css/bootstrap.css';

var App = View.extend({
    /**
     * @param {object} [settings]
     * @param {bool} [settings.start=true] Run start after initialization
     */
    initialize: function (settings) {
        this._started = false;
        settings = settings || {};
        if (settings.start === undefined || settings.start) {
            this.start();
        }
    },

    /**
     * Start the application with optional components.
     * @param {object} [settings]
     * @param {bool} [settings.fetch=true] Fetch the current user modal
     * @param {bool} [settings.render=true] Render the layout after starting
     * @param {bool} [settings.history=true] Start backbone's history api
     * @returns {$.Deferred} A promise-like object that resolves when the app is ready
     */
    start: function (settings) {
        // start is a noop if the app is already running
        var promise = new $.Deferred().resolve(null).promise();
        if (this._started) {
            return promise;
        }

        // set defaults
        settings = _.defaults(settings || {}, {
            fetch: true,
            render: true,
            history: true
        });

        // define a function to be run after fetching the user model
        var afterFetch = _.bind(function (user) {
            this._createLayout();

            if (user) {
                setCurrentUser(new UserModel(user));
                eventStream.open();
            }

            this._started = true;

            if (settings.render) {
                this.render();
            }

            if (settings.history) {
                Backbone.history.stop();
                Backbone.history.start({
                    pushState: false
                });
            }
        }, this);

        // If fetching the user from the server then we return the jqxhr object
        // from the request, otherwise just call the callback.
        if (settings.fetch) {
            promise = fetchCurrentUser()
                .done(afterFetch);
        } else {
            afterFetch(null);
        }

        this.bindGirderEvents();
        return promise;
    },

    /**
     * Bind the application to the global event object.
     */
    bindGirderEvents: function () {
        // Unbind any current handlers in case this happens to be called twice.
        events.off(null, null, this);

        events.on('g:navigateTo', this.navigateTo, this);
        events.on('g:loginUi', this.loginDialog, this);
        events.on('g:registerUi', this.registerDialog, this);
        events.on('g:resetPasswordUi', this.resetPasswordDialog, this);
        events.on('g:alert', this.alert, this);
        events.on('g:login', this.login, this);
    },

    /**
     * Create the main layout views.
     * @private
     */
    _createLayout: function () {
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
            eventStream: eventStream,
            parentView: this
        });

        this.layoutRenderMap = {};
        this.layoutRenderMap[Layout.DEFAULT] = this._defaultLayout;
        this.layoutRenderMap[Layout.EMPTY] = this._emptyLayout;
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
        if (!this._started) {
            return;
        }
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
        if (getCurrentUser()) {
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
        eventStream.close();

        if (getCurrentUser()) {
            eventStream.open();
            router.navigate(route, {trigger: true});
        } else {
            router.navigate('/', {trigger: true});
        }
    }
});

export default App;
