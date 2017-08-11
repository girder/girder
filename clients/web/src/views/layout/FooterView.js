import View from 'girder/views/View';
import { getApiRoot } from 'girder/rest';

import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.pug';

import 'girder/stylesheets/layout/footer.styl';

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({

    initialize: function (settings) {
        const mail = settings.contactEmail || '';
        if (mail !== '') {
            this.emailHref = 'mailto:' + mail;
        }
    },

    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: getApiRoot(),
            contactHref: this.emailHref || ''
        }));
        return this;
    }
});

export default LayoutFooterView;
