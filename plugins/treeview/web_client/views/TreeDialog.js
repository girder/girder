import View from 'girder/views/View';

import TreeView from './TreeView';

import treeDialog from '../templates/treeDialog.pug';
import '../stylesheets/treeDialog.styl';

const TreeDialog = View.extend({
    events: {
        'click .g-submit-button': '_submit'
    },

    initialize(settings) {
        this.treeView = new TreeView({
            parentView: this
        });
        this.listenTo(this.treeView, 'g:treeview:select', this._select);
    },

    render() {
        this.$el.html(
            treeDialog({
                title: 'some title',
                help: 'some help',
                submit: 'OK',
                label: 'selected'
            })
        ).girderModal(this);

        this.treeView.setElement(
            this.$('.g-treeview-container')
        ).render();
    },

    _select(model, node) {
        this.$('#g-treeview-selected').val(
            this.treeView.path(node)
        );
    },

    _submit() {
    }
});

export default TreeDialog;
