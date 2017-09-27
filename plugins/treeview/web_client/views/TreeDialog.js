import _ from 'underscore';

import View from 'girder/views/View';

import TreeView from './TreeView';

import treeDialog from '../templates/treeDialog.pug';
import '../stylesheets/treeDialog.styl';

/**
 * This view is a modal dialog for selecting arbitrary documents.
 * It is primarly used as a parent view for more specific modal
 * modal dialogs.
 */
const TreeDialog = View.extend({
    events: {
        'click .g-submit-button': '_submit'
    },

    initialize(settings = {}) {
        this.settings = _.defaults(settings, {
            title: 'Select a document',
            placeholder: 'Click on a document to select it.',
            label: 'Selected',
            submit: 'Save',
            readonly: true
        });
        this.treeView = new TreeView(_.defaults(settings.treeview || {}, {
            parentView: this
        }));
        this.listenTo(this.treeView, 'g:treeview:select', this._select);
    },

    render() {
        this.$el.html(
            treeDialog(this.settings)
        ).girderModal(this);

        this.treeView.setElement(
            this.$('.g-treeview-container')
        ).render();
        return this;
    },

    _select(model, node) {
        this.$('#g-treeview-selected').val(
            this.treeView.path(node)
        );
    },

    _submit() {
        const selected = this.treeView.getSelected();
        const models = _.map(selected, _.property('model'));
        const paths = _.map(selected, (s) => this.treeView.path(s));
        this.$el.modal('hide');
        this.trigger('g:saved', {selected, models, paths});
    }
});

export default TreeDialog;
