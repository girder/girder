import LoadingAnimationTemplate from 'girder/templates/widgets/loadingAnimation.jade';
import View from 'girder/view';

/**
 * This widget can be used to display a small loading animation.
 */
var LoadingAnimation = View.extend({
    render: function () {
        this.$el.html(LoadingAnimationTemplate());
        return this;
    }
});

export default LoadingAnimation;
