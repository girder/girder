import _ from 'underscore';

import FrontPageView from 'girder/views/body/FrontPageView';
import { renderMarkdown } from 'girder/misc';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

wrap(FrontPageView, 'render', function (render) {
    restRequest({
        type: 'GET',
        path: 'homepage/markdown'
    }).done(_.bind(function (resp) {
        this.$el.html(renderMarkdown(resp['homepage.markdown']));
    }, this));

    return this;
});
