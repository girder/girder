var girder = require('girder/init');
var View   = require('girder/view');
var Rest   = require('girder/rest');

/**
 * This view shows the footer in the layout.
 */
var LayoutFooterView = View.extend({
    render: function () {
        this.$el.html(girder.templates.layoutFooter({
            apiRoot: Rest.apiRoot
        }));
        return this;
    }
});

module.exports = LayoutFooterView;

