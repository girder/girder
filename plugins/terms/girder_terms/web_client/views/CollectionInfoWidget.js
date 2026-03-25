import CollectionInfoWidgetTemplate from '../templates/collectionInfoWidget.pug';
import '../stylesheets/collectionInfoWidget.styl';

const $ = girder.$;
const { renderMarkdown } = girder.misc;
const { wrap } = girder.utilities.PluginUtils;
const CollectionInfoWidget = girder.views.widgets.CollectionInfoWidget;

wrap(CollectionInfoWidget, 'render', function (render) {
    render.call(this);

    if (this.model.get('terms')) {
        const newEl = $(CollectionInfoWidgetTemplate({
            collection: this.model,
            renderMarkdown: renderMarkdown
        }));
        this.$('.modal-body>.g-info-dialog-description').after(newEl);
    }

    return this;
});
