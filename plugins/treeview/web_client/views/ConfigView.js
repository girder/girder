import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';

import TreeDialog from './TreeDialog';
import TreeView from './TreeView';

import configView from '../templates/configView.pug';
import '../stylesheets/configView.styl';

const ConfigView = View.extend({
    events: {
        'click .g-treeview-generic-dialog-button': '_genericDialog'
    },

    initialize() {
        this.treeView = new TreeView({parentView: this});
        this.render();
    },

    render() {
        this.$el.html(configView());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Tree view',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            });
        }

        this.breadcrumb.render();

        this.treeView.setElement(this.$('.g-treeview-container')).render();

        return this;
    },

    _genericDialog() {
        const dialog = new TreeDialog({
            parentView: this,
            el: '#g-dialog-container'
        });
        this.listenTo(dialog, 'g:saved', (obj) => {
            this.$('#g-treeview-generic-dialog').val(obj.paths.join(', '));
        });
        dialog.render();
    }
});

export default ConfigView;
