
import { getCurrentUser } from '@girder/core/auth';
import { AccessType } from '@girder/core/constants';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';

import ItemView from '@girder/core/views/body/ItemView';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';

import DicomItemView from './views/DicomView';
import ParseDicomItemTemplate from './templates/parseDicomItem.pug';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        // Add a button to force DICOM extraction
        if (this.model.get('_accessLevel') >= AccessType.WRITE) {
            this.$('.g-item-actions-menu').prepend(ParseDicomItemTemplate({
                item: this.model,
                currentUser: getCurrentUser()
            }));
        }

        if (this.model.has('dicom')) {
            new DicomItemView({
                parentView: this,
                item: this.model
            })
                .render()
                .$el.insertAfter(this.$('.g-item-info'));
        }
    });
    return render.call(this);
});

ItemView.prototype.events['click .g-dicom-parse-item'] = function () {
    restRequest({
        method: 'POST',
        url: `item/${this.model.id}/parseDicom`,
        error: null
    })
        .done((resp) => {
            // Show up a message to alert the user it was done
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Dicom item parsed.',
                type: 'success',
                timeout: 4000
            });
        })
        .fail((resp) => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: 'No Dicom metadata.',
                type: 'danger',
                timeout: 4000
            });
        });
};

SearchFieldWidget.addMode(
    'dicom',
    ['item'],
    'DICOM metadata search',
    `You are searching for text in DICOM metadata. Only Girder items which have been preprocessed to
        extract DICOM images will be searched. The search text may appear anywhere within the common (i.e.
        shared across slices) metadata keys or values of a DICOM image.`
);
