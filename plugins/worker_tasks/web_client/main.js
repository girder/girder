import './routes';
import { wrap } from 'girder/utilities/PluginUtils';
import GlobalNavView from 'girder/views/layout/GlobalNavView';

// Add a new global nav item for running analyses
wrap(GlobalNavView, 'initialize', function (initialize) {
    initialize.apply(this, arguments);

    this.defaultNavItems.push({
        name: 'Tasks',
        icon: 'icon-cog-alt',
        target: 'worker_tasks'
    });
});
