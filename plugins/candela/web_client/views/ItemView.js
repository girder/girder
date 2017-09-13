import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import CandelaWidget from './CandelaWidget';

wrap(ItemView, 'render', function (render) {
    this.model.getAccessLevel((accessLevel) => {
        // Because the passthrough call to render() also does an async call to
        // getAccessLevel(), wait until this one completes before invoking that
        // one.
        //
        // Furthermore, we need to call this *first*, because of how the Candela
        // view inserts itself into the app-body-container, which doesn't seem
        // to exist until the passthrough call is made.
        render.call(this);

        if (this.candelaWidget) {
            this.candelaWidget.remove();
        }

        this.candelaWidget = new CandelaWidget({
            className: 'g-candela-container',
            item: this.model,
            accessLevel: accessLevel,
            parentView: this
        });
        this.candelaWidget.$el.appendTo(this.$el);
    });

    return this;
});
