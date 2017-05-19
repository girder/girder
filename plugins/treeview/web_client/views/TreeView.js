import View from 'girder/views/View';

import attach from '../attach';

const TreeView = View.extend({
    events: {
        'changed.jstree': '_onChanged'
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

    _destroy() {
        this.$el.jstree('destroy');
    },

    _onChanged(e, data) {
        this.trigger(
            'g:treeview:select', {

            }
        );
    }
});

export default TreeView;
