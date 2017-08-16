import View from 'girder/views/View';
import { getApiRoot } from 'girder/rest';

import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.pug';

import 'girder/stylesheets/layout/footer.styl';

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({

    initialize: function (settings) {
        const contactEmail = settings.contactEmail || null;
        this.contactHref = contactEmail !== null ? `mailto:${contactEmail}` : null;
    },

    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: getApiRoot(),
            contactHref: this.contactHref
        }));
        return this;
    }
});

export default LayoutFooterView;
