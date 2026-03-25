
import ReadmeWidgetTemplate from '../templates/readmeWidget.pug';

import '../stylesheets/readmeWidget.styl';

const $ = girder.$;
const HierarchyWidget = girder.views.widgets.HierarchyWidget;
const { wrap } = girder.utilities.PluginUtils;
const { restRequest } = girder.rest;
const { renderMarkdown } = girder.misc;

// Add a README widget to all folders which contain an item that starts with `README`
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder') {
        const id = this.parentModel.get('_id');

        restRequest({ url: `folder/${id}/readme`, method: 'GET' })
            .then((resp) => {
                if (resp) {
                    $('.g-folder-metadata').after(ReadmeWidgetTemplate);
                    renderMarkdown(resp, $('.g-widget-readme-content'));
                }
                return resp;
            });
    }
    return this;
});
