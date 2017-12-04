import './routes';
import './views/FrontPageView';

import { registerPluginNamespace } from 'girder/pluginUtils';

import * as {{ cookiecutter.plugin_camel_case }} from './index';

registerPluginNamespace('{{ cookiecutter.plugin_name }}', {{ cookiecutter.plugin_camel_case }});
