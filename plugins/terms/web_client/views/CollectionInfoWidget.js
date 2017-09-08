import $ from 'jquery';

import { renderMarkdown } from 'girder/misc';
import CollectionInfoWidget from 'girder/views/widgets/CollectionInfoWidget';
import { wrap } from 'girder/utilities/PluginUtils';

import CollectionInfoWidgetTemplate from '../templates/collectionInfoWidget.pug';
import '../stylesheets/collectionInfoWidget.styl';

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
