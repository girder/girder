var $                 = require('jquery');

var Auth              = require('girder/auth');
var Events            = require('girder/events');
var FrontPageTemplate = require('girder/templates/body/frontPage.jade');
var Rest              = require('girder/rest');
var Router            = require('girder/router');
var versionInfo       = require('girder/girder-version');
var View              = require('girder/view');

/**
 * This is the view for the front page of the app.
 */
var FrontPageView = View.extend({
    events: {
        'click .g-register-link': function () {
            Events.trigger('g:registerUi');
        },
        'click .g-login-link': function () {
            Events.trigger('g:loginUi');
        },
        'click .g-collections-link': function () {
            Router.navigate('collections', {trigger: true});
        },
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        },
        'click .g-my-account-link': function () {
            Router.navigate('useraccount/' + Auth.getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        },
        'click .g-my-folders-link': function () {
            Router.navigate('user/' + Auth.getCurrentUser().get('_id'), {trigger: true});
        }
    },

    initialize: function () {
        Rest.cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        this.$el.html(FrontPageTemplate({
            apiRoot: Rest.apiRoot,
            staticRoot: Rest.staticRoot,
            currentUser: Auth.getCurrentUser(),
            versionInfo: versionInfo
        }));

        return this;
    }
});

module.exports = FrontPageView;

Router.route('', 'index', function () {
    Events.trigger('g:navigateTo', FrontPageView);
});
