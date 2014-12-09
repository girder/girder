/**
 * This is the view for the front page of the app.
 */
girder.views.FrontPageView = girder.View.extend({
    events: {
        'click .g-register-link': function () {
            girder.events.trigger('g:registerUi');
        },
        'click .g-login-link': function () {
            girder.events.trigger('g:loginUi');
        },
        'click .g-collections-link': function () {
            girder.router.navigate('collections', {trigger: true});
        },
        'click .g-quicksearch-link': function () {
            $('.g-quick-search-container .g-search-field').focus();
        },
        'click .g-my-account-link': function () {
            girder.router.navigate('useraccount/' + girder.currentUser.get('_id') +
                                   '/info', {trigger: true});
        },
        'click .g-my-folders-link': function () {
            girder.router.navigate('user/' + girder.currentUser.get('_id'), {trigger: true});
        }
    },

    initialize: function () {
        girder.cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.frontPage({
            apiRoot: girder.apiRoot,
            staticRoot: girder.staticRoot,
            currentUser: girder.currentUser,
            versionInfo: girder.versionInfo
        }));

        return this;
    }
});

girder.router.route('', 'index', function () {
    girder.events.trigger('g:navigateTo', girder.views.FrontPageView);
});
