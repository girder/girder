import DicomView from './views/DicomView';
import { wrap } from 'girder/utilities/PluginUtils';
import ItemView from 'girder/views/body/ItemView';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        this.$('.g-item-header').after('<div class="g-dicom-view"></div>');
        const view = new DicomView({
            el: this.$('.g-dicom-view'),
            parentView: this,
            item: this.model
        });
        view.render();
    }, this);
    return render.call(this);
});
