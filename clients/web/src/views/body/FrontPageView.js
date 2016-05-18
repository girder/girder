var $             = require('jquery');
var girder        = require('girder/init');
var Rest          = require('girder/rest');
var Auth          = require('girder/auth');
var Events        = require('girder/events');
var versionInfo   = require('girder/girder-version');
var View          = require('girder/view');
var MiscFunctions = require('girder/utilities/MiscFunctions');

var FrontPageTemplate = require('girder/templates/body/frontPage.jade');

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
            girder.router.navigate('collections', {trigger: true});
        },
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        },
        'click .g-my-account-link': function () {
            girder.router.navigate('useraccount/' + Auth.getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        },
        'click .g-my-folders-link': function () {
            girder.router.navigate('user/' + Auth.getCurrentUser().get('_id'), {trigger: true});
        }
    },

    initialize: function () {
        MiscFunctions.cancelRestRequests('fetch');
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

girder.router.route('', 'index', function () {
    Events.trigger('g:navigateTo', FrontPageView);
});
