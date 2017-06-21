import FrontPageView from 'girder/views/body/FrontPageView';
import { wrap } from 'girder/utilities/PluginUtils';

// For more information on creating new views, see:
// http://girder.readthedocs.io/en/latest/development.html#client-development

// For more information on wrapping views, see:
// http://girder.readthedocs.io/en/latest/plugin-development.html#javascript-extension-capabilities
wrap(FrontPageView, 'render', function (render) {
    render.call(this);

    this.$el.append('<p>Hi from {{ cookiecutter.plugin_nice_name }}</p>');

    return this;
});
