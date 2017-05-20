import View from 'girder/views/View';

import attach from '../attach';
import { model } from '../utils/node';

const TreeView = View.extend({
    events: {
        'select_node.jstree': '_onSelect'
    },

    initialize(settings) {
    },

    render() {
        this._destroy();
        attach(this.el);
    },

    destroy() {
        this._destroy();
        return View.prototype.destroy.apply(this, arguments);
    },

    instance() {
        return this.$el.jstree(true);
    },

    saveState() {
        this.instance().save_state();
    },

    clearState() {
        this.instance().clear_state();
    },

    reload() {
        return new Promise((resolve) => {
            this.$el.one('refresh.jstree', () => resolve(this));
            this.instance().refresh();
        });
    },

    path(node) {
        return '/' + this.instance().get_path(node).join('/');
    },

    _destroy() {
        this.$el.jstree('destroy');
    },

    _onSelect(e, data) {
        const node = data.node;
        const event = 'g:treeview:select';

        if (node) {
            const modelObj = model(node);

            if (modelObj) {
                const type = modelObj._modelType;
                this.trigger(
                    `${event}:${type}`, modelObj, node, data.selected
                );
            }

            this.trigger(
                event, null, data.node, data.selected
            );
        }
    }
});

export default TreeView;
