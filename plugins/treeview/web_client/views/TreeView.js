import _ from 'underscore';
import $ from 'jquery';

import View from 'girder/views/View';

import jstree from '../jstree';
import { model } from '../utils/node';

const TreeView = View.extend({
    events: {
        'select_node.jstree': '_onSelect',
        'state_ready.jstree': '_onLoad'
    },

    initialize(settings = {}) {
        this.loaded = false;
        this.jstreeConfig = {
            core: {
                multiple: settings.multiple,
                check_callback: settings.check_callback
            }
        };

        if (settings.selectable) {
            this.jstreeConfig.selectable = settings.selectable;
        }
    },

    render() {
        this._destroy();
        jstree(this.el, this.jstreeConfig);
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
        const defer = $.Deferred();
        this.$el.one('refresh.jstree', () => defer.resolve(this));
        this.instance().refresh();
        return defer.promise();
    },

    path(node) {
        return '/' + this.instance().get_path(node).join('/');
    },

    select(node) {
    },

    _destroy() {
        this.$el.jstree('destroy');
    },

    getSelected() {
        return _.map(
            this.instance().get_selected(true),
            _.property('original')
        );
    },

    _onSelect(e, data) {
        // Ignore initial selection events because they are fired
        // when reloading the state and may contain invalid selections.
        if (!this.loaded) {
            return;
        }
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
                event, modelObj, data.node, data.selected
            );
        }
    },

    _onLoad() {
        this.loaded = true;
        this.trigger('g:treeview:load', this);
    }
});

export default TreeView;
