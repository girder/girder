import $ from 'jquery';

import View from 'girder/views/View';
import { cancelRestRequests, getApiRoot } from 'girder/rest';
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
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.brandName = settings.brandName || 'Girder';
        this.render();
    },

    render: function () {
        this.$el.html(FrontPageTemplate({
            apiRoot: getApiRoot(),
            currentUser: getCurrentUser(),
            brandName: this.brandName
        }));

        return this;
    }
});

export default FrontPageView;
