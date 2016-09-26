import $ from 'jquery';

import router from 'girder/router';
import versionInfo from 'girder/version';
import View from 'girder/views/View';
import { cancelRestRequests, apiRoot, staticRoot } from 'girder/rest';
import events from 'girder/events';
import { getCurrentUser } from 'girder/auth';

import FrontPageTemplate from 'girder/templates/body/frontPage.pug';

import 'girder/stylesheets/body/frontPage.styl';

/**
 * This is the view for the front page of the app.
 */
var FrontPageView = View.extend({
    events: {
        'click .g-register-link': function () {
            events.trigger('g:registerUi');
        },
        'click .g-login-link': function () {
            events.trigger('g:loginUi');
        },
        'click .g-collections-link': function () {
            router.navigate('collections', {trigger: true});
        },
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        },
        'click .g-my-account-link': function () {
            router.navigate('useraccount/' + getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        },
        'click .g-my-folders-link': function () {
            router.navigate('user/' + getCurrentUser().get('_id'), {trigger: true});
        }
    },

    initialize: function () {
        cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        this.$el.html(FrontPageTemplate({
            apiRoot: apiRoot,
            staticRoot: staticRoot,
            currentUser: getCurrentUser(),
            versionInfo: versionInfo
        }));

        return this;
    }
});

export default FrontPageView;
