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

    _submit() {
    }
});

export default TreeDialog;
