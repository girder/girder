import _ from 'underscore';

import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import VegaWidget from './VegaWidget';

wrap(ItemView, 'render', function (render) {
    this.model.getAccessLevel(_.bind(function (accessLevel) {
        // Because the passthrough call to render() also does an async call to
        // getAccessLevel(), wait until this one completes before invoking that
        // one.
        //
        // Furthermore, we need to call this *first*, because of how the Vega
        // view inserts itself into the app-body-container, which doesn't seem
        // to exist until the passthrough call is made.
        render.call(this);

        this.vegaWidget = new VegaWidget({
            item: this.model,
            accessLevel: accessLevel,
            parentView: this
        });
    }, this));

    return this;
});
