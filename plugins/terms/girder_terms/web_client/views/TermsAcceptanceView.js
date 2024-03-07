import TermsAcceptanceTemplate from '../templates/termsAcceptance.pug';
import '../stylesheets/termsAcceptance.styl';

const Backbone = girder.Backbone;
const { renderMarkdown } = girder.misc;
const View = girder.views.View;
const router = girder.router;

const TermsAcceptanceView = View.extend({
    events: {
        'click #g-terms-accept': async function (event) {
            const buttons = this.$('button');
            buttons.girderEnable(false);

            await this.model.currentUserSetAcceptTerms();

            buttons.girderEnable(true);

            // Re-route to the current page, without reloading the DOM
            Backbone.history.loadUrl(Backbone.history.getHash());
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
