import { Girder } from '@girder/core';

export const initFrontPageView = (girder: Girder) => {
    const {
        views: { body: { FrontPageView } },
        misc: { renderMarkdown },
        rest: { restRequest, getApiRoot },
        utilities: { PluginUtils: { wrap }},
    } = girder;

    wrap(FrontPageView, 'render', function (render) {
        restRequest({
            method: 'GET',
            url: 'homepage'
        }).done((resp) => {
            if (!resp['homepage.markdown']) {
                render.call(this);
                if (resp['homepage.header']) {
                    this.$('.g-frontpage-title').text(resp['homepage.header']);
                }
                if (resp['homepage.subheader']) {
                    this.$('.g-frontpage-subtitle').text(resp['homepage.subheader']);
                }
                if (resp['homepage.welcome_text']) {
                    this.$('.g-frontpage-welcome-text-content').html(renderMarkdown(resp['homepage.welcome_text']));
                }
                if (resp['homepage.logo']) {
                    const logoUrl = `${getApiRoot()}/file/${resp['homepage.logo']}/download?contentDisposition=inline`;
                    this.$('.g-frontpage-logo').attr('src', logoUrl);
                }
            } else {
                this.$el.html(renderMarkdown(resp['homepage.markdown']));
            }
        });

        return this;
    });
};
