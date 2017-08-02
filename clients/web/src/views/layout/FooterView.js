import View from 'girder/views/View';
import { getApiRoot } from 'girder/rest';

import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.pug';

import 'girder/stylesheets/layout/footer.styl';

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({
    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: getApiRoot()
        }));
        return this;
    }
});

export default LayoutFooterView;
