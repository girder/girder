import View from '@girder/core/views/View';

import LoadingAnimationTemplate from '@girder/core/templates/widgets/loadingAnimation.pug';

import '@girder/core/stylesheets/layout/loading.styl';

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
