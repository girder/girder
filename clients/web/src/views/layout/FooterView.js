import LayoutFooterTemplate from 'girder/templates/layout/layoutFooter.jade';
import Rest                 from 'girder/rest';
import View                 from 'girder/view';

/**
 * This view shows the footer in the layout.
 */
export var LayoutFooterView = View.extend({
    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: Rest.apiRoot
        }));
        return this;
    }
});

