import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';

import FileDialog from './FileDialog';
import FolderDialog from './FolderDialog';
import ItemDialog from './ItemDialog';
import TreeDialog from './TreeDialog';
import TreeView from './TreeView';

import configView from '../templates/configView.pug';
import '../stylesheets/configView.styl';

/**
 * This view is added to the treeview plugin configuration page
 * to serve both as a demo of what the plugin does and an example
 * of how to use it with other views.
 */
const ConfigView = View.extend({
    events: {
        'click .g-treeview-generic-dialog-button': '_genericDialog',
        'click .g-treeview-folder-dialog-button': '_folderDialog',
        'click .g-treeview-item-dialog-button': '_itemDialog',
        'click .g-treeview-file-dialog-button': '_fileDialog'
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
        this.listenTo(this.treeView, 'g:treeview:select', (model) => {
            this.$('.g-treeview-selected').text(
                JSON.stringify(model, null, 2)
            );
        });

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
    },

    _folderDialog() {
        const dialog = new FolderDialog({
            parentView: this,
            el: '#g-dialog-container'
        });
        this.listenTo(dialog, 'g:saved', (obj) => {
            this.$('#g-treeview-folder-dialog').val(obj.paths.join(', '));
        });
        dialog.render();
    },

    _itemDialog() {
        const dialog = new ItemDialog({
            parentView: this,
            el: '#g-dialog-container'
        });
        this.listenTo(dialog, 'g:saved', (obj) => {
            this.$('#g-treeview-item-dialog').val(obj.paths.join(', '));
        });
        dialog.render();
    },

    _fileDialog() {
        const dialog = new FileDialog({
            parentView: this,
            el: '#g-dialog-container'
        });
        this.listenTo(dialog, 'g:saved', (obj) => {
            this.$('#g-treeview-file-dialog').val(obj.paths.join(', '));
        });
        dialog.render();
    }
});

export default ConfigView;
