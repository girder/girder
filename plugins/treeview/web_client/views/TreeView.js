import View from 'girder/views/View';

import attach from '../attach';

const TreeView = View.extend({
    initialize(settings) {
    },

    render() {
        attach(this.el);
    }
});

export default TreeView;
