import WidgetModel from '../models/WidgetModel';

const Backbone = girder.Backbone;

const WidgetCollection = Backbone.Collection.extend({
    model: WidgetModel,

    /**
     * Get an object containing all of the current parameter values as
     *   modelId -> value
     */
    values() {
        const params = {};
        this.each((m) => {
            // apply special handling for certain parameter types
            // https://github.com/DigitalSlideArchive/slicer/blob/9e5112ab3444ad8c699d70452a5fe4a74ebbc778/server/__init__.py#L44-L46
            switch (m.get('type')) {
                case 'file':
                case 'item':
                case 'image':
                case 'directory':
                    params[m.id] = m.value().id;
                    break;
                case 'multi':
                case 'new-file':
                    if (m && m.value && m.value()) {
                        params[m.id + '_folder'] = m.value().get('folderId');
                        params[m.id] = m.value().get('name');
                    }
                    break;
                case 'string':
                case 'boolean':
                case 'integer':
                case 'float':
                case 'double':
                case 'string-enumeration':
                    params[m.id] = m.value();
                    break;
                default:
                    params[m.id] = JSON.stringify(m.value());
            }
        });
        return params;
    }
});

export default WidgetCollection;
