var View   = require('girder/view');
var Rest   = require('girder/rest');

var LayoutFooterTemplate = require('girder/templates/layout/layoutFooter.jade');

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({
    render: function () {
        this.$el.html(LayoutFooterTemplate({
            apiRoot: Rest.apiRoot
        }));
        return this;
    }
});

module.exports = LayoutFooterView;

