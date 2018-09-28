import Backbone from 'backbone';

import WidgetModel from '../models/WidgetModel';

var WidgetCollection = Backbone.Collection.extend({
    model: WidgetModel,

    /**
     * Get an object containing all of the current parameter values as
     *   modelId -> value
     */
    values: function () {
        var params = {};
        this.each(function (m) {
            // apply special handling for certain parameter types
            // https://github.com/DigitalSlideArchive/slicer/blob/9e5112ab3444ad8c699d70452a5fe4a74ebbc778/server/__init__.py#L44-L46
            switch (m.get('type')) {
                case 'file':
                    params[m.id + '_girderItemId'] = m.value().id;
                    break;
                case 'new-file':
                    params[m.id + '_girderFolderId'] = m.value().get('folderId');
                    params[m.id + '_name'] = m.value().get('name');
                    break;
                case 'new-folder':
                    params[m.id + '_girderFolderId'] = m.value().get('folderId');
                    params[m.id + '_name'] = m.value().get('name');
                    break;
                case 'image':
                    params[m.id + '_girderFileId'] = m.value().id;
                    break;
                default:
                    params[m.id] = JSON.stringify(m.value());
            }
        });
        return params;
    }
});

export default WidgetCollection;
