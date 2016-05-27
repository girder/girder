import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.jade';
import { apiRoot } from 'girder/rest';
import View from 'girder/view';

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

