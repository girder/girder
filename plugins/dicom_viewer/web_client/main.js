import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';
import ItemView from 'girder/views/body/ItemView';

import DicomItemView from './views/DicomView';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        restRequest({
            url: `item/${this.model.id}/dicom`,
            data: {
                // don't need the dicom tags, just want the sorted results
                filters: 'dummy'
            }
        }).done((resp) => {
            if (resp.length) {
                new DicomItemView({
                    parentView: this,
                    files: resp
                })
                    .render()
                    .$el.insertAfter(this.$('.g-item-info'));
            }
        });
    });
    return render.call(this);
});
