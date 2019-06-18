import $ from 'jquery';

import { renderMarkdown } from '@girder/core/misc';
import CollectionInfoWidget from '@girder/core/views/widgets/CollectionInfoWidget';
import { wrap } from '@girder/core/utilities/PluginUtils';

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
