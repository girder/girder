import View from '@girder/core/views/View';
import { getApiRoot } from '@girder/core/rest';

import LayoutFooterTemplate from '@girder/core/templates/layout/layoutFooter.pug';

import '@girder/core/stylesheets/layout/footer.styl';

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({

    initialize: function (settings) {
        const contactEmail = settings.contactEmail || null;
        this.contactHref = contactEmail !== null ? `mailto:${contactEmail}` : null;
        this.privacyNoticeHref = settings.privacyNoticeHref || null;
    },

    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: getApiRoot(),
            contactHref: this.contactHref,
            privacyNoticeLink: this.privacyNoticeHref
        }));
        return this;
    }
});

export default LayoutFooterView;
