import Backbone from 'backbone';

import { renderMarkdown } from '@girder/core/misc';
import router from '@girder/core/router';
import View from '@girder/core/views/View';

import TermsAcceptanceTemplate from '../templates/termsAcceptance.pug';
import '../stylesheets/termsAcceptance.styl';

const TermsAcceptanceView = View.extend({
    events: {
        'click #g-terms-accept': function (event) {
            const buttons = this.$('button');
            buttons.girderEnable(false);

            this.model.currentUserSetAcceptTerms()
                // This is never expected to fail, but use "always" for safety
                .always(() => {
                    buttons.girderEnable(true);
                    // Re-route to the current page, without reloading the DOM
                    Backbone.history.loadUrl(Backbone.history.getHash());
                });
        },
        'click #g-terms-reject': function (event) {
            // Route to home page
            router.navigate('', { trigger: true });
        }
    },

    /**
     * @param {CollectionModel} settings.collection - The collection to display the terms for.
     */
    initialize: function (settings) {
        this.model = settings.collection;
        this.render();
    },

    render: function () {
        this.$el.html(TermsAcceptanceTemplate({
            collection: this.model,
            renderMarkdown: renderMarkdown
        }));

        return this;
    }
});

export default TermsAcceptanceView;
