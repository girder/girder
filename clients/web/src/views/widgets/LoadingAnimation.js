var LoadingAnimationTemplate = require('girder/templates/widgets/loadingAnimation.jade');
var View                     = require('girder/view');

/**
 * This widget can be used to display a small loading animation.
 */
var LoadingAnimation = View.extend({
    render: function () {
        this.$el.html(LoadingAnimationTemplate());
        return this;
    }
});

module.exports = LoadingAnimation;
