import { getCurrentUser } from 'girder/auth';
import { AccessType } from 'girder/constants';
import events from 'girder/events';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';
import ItemView from 'girder/views/body/ItemView';

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
