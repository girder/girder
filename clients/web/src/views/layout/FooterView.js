import View from 'girder/views/View';
import { apiRoot } from 'girder/rest';

import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.pug';

import 'girder/stylesheets/layout/footer.styl';

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({
    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: apiRoot
        }));
        return this;
    }
});

export default LayoutFooterView;

