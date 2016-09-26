import View from 'girder/views/View';

import LoadingAnimationTemplate from 'girder/templates/widgets/loadingAnimation.pug';

import 'girder/stylesheets/layout/loading.styl';

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
