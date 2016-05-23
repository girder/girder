import $                 from 'jquery';

import Auth              from 'girder/auth';
import Events            from 'girder/events';
import FrontPageTemplate from 'girder/templates/body/frontPage.jade';
import Rest              from 'girder/rest';
import router            from 'girder/router';
import versionInfo       from 'girder/girder-version';
import View              from 'girder/view';

/**
 * This is the view for the front page of the app.
 */
export var FrontPageView = View.extend({
    events: {
        'click .g-register-link': function () {
            Events.trigger('g:registerUi');
        },
        'click .g-login-link': function () {
            Events.trigger('g:loginUi');
        },
        'click .g-collections-link': function () {
            router.navigate('collections', {trigger: true});
        },
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        },
        'click .g-my-account-link': function () {
            router.navigate('useraccount/' + Auth.getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        },
        'click .g-my-folders-link': function () {
            router.navigate('user/' + Auth.getCurrentUser().get('_id'), {trigger: true});
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

router.route('', 'index', function () {
    Events.trigger('g:navigateTo', FrontPageView);
});
