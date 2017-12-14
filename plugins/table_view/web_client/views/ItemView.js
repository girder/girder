import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import TableWidget from './TableWidget';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.tableWidget) {
            this.tableWidget.remove();
        }

        this.tableWidget = new TableWidget({
            el: $('<div>', {class: 'g-table-view-container'})
                .insertAfter(this.$('.g-item-info')),
            files: this.fileListWidget.collection,
            parentView: this
        });
    });
    return render.call(this);
});
