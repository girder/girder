var girder = require('girder/init');
var View   = require('girder/view');

/**
 * This widget can be used to display a small loading animation.
 */
var LoadingAnimation = View.extend({
    render: function () {
        this.$el.html(girder.templates.loadingAnimation());
        return this;
    }
});

module.exports = LoadingAnimation;
