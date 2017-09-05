import _ from 'underscore';

import FrontPageView from 'girder/views/body/FrontPageView';
import { renderMarkdown } from 'girder/misc';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

wrap(FrontPageView, 'render', function (render) {
    restRequest({
        method: 'GET',
        url: 'homepage/markdown'
    }).done(_.bind(function (resp) {
        if (resp['homepage.markdown'] === '') {
            restRequest({
                method: 'GET',
                url: 'homepage/settings'
            }).done(_.bind(function (res) {
                _.bind(render, this)();
                console.log(this.$('.g-frontpage-subtitle').text());
                console.log(res['homepage.header']);
                if (res['homepage.header'] !== '') {
                    this.$('.g-frontpage-title').text(res['homepage.header']);
                }
                if (res['homepage.subheading_text'] !== '') {
                    this.$('.g-frontpage-subtitle').text(res['homepage.subheading_text']);
                }
                if (res['homepage.welcome_text'] !== '') {
                    this.$('.g-frontpage-welcome-text').text(res['homepage.welcome_text']);
                }
            }, this));
        } else {
            this.$el.html(renderMarkdown(resp['homepage.markdown']));
        }
    }, this));

    return this;
});
