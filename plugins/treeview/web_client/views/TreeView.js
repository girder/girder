import View from 'girder/views/View';

import attach from '../attach';

const TreeView = View.extend({
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

    _destroy() {
        this.$el.jstree('destroy');
    }
});

export default TreeView;
