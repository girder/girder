import _ from 'underscore';
import $ from 'jquery';

import View from 'girder/views/View';

import { model } from '../utils/node';
import jstree from '../jstree';

/**
 * This view is wrapper around the jstree interface allowing it to
 * be used like a normal girder view.  It wraps a number of the
 * methods provided by jstree to provide an abstract interface.
 */
const TreeView = View.extend({
    events: {
        'select_node.jstree': '_onSelect',
        'state_ready.jstree': '_onLoad',
        'before_open.jstree': '_triggerEvent',
        'after_open.jstree': '_triggerEvent',
        'after_close.jstree': '_triggerEvent',
        'model.jstree': '_triggerEvent'
    },

    /**
     * Initialize the view.
     *
     * @param {boolean} [settings.multiple=false]
     *   Allow multiselection with ctrl/shift keys.
     * @param {string[]} [settings.selectable]
     *   A list of selectable types.
     */
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
        return this;
    },

    destroy() {
        this._destroy();
        return View.prototype.destroy.apply(this, arguments);
    },

    /**
     * Get the jstree instance created when rendering for directly
     * interacting with the tree.
     */
    instance() {
        return this.$el.jstree(true);
    },

    /**
     * Save the tree state in local storage.  This uses jstree's `state`
     * plugin to store a serialized version of the tree state in local
     * storage so it persists between renders.  This generally isn't
     * necessary to be called because jstree automatically handles it.
     */
    saveState() {
        this.instance().save_state();
    },

    /**
     * Forcibly clear the saved state of the tree.
     */
    clearState() {
        this.instance().clear_state();
    },

    /**
     * Reload the full tree from the server.  This may be necessary
     * if models are created, modified, or destroyed outside of this
     * view.
     *
     * @returns {Promise} Resolves when the tree is reloaded.
     */
    reload() {
        const defer = $.Deferred();
        this.$el.one('refresh.jstree', () => defer.resolve(this));
        this.instance().refresh();
        return defer.promise();
    },

    /**
     * Get a path string to a node for a human readable representation
     * of the node.
     * (WARNING: the path to a resource is not necessarily unique)
     */
    path(node) {
        return '/' + this.instance().get_path(node).join('/');
    },

    /**
     * Get a list of selected nodes.  If multiselect is turned off
     * this will be an array with at most one node.
     */
    getSelected() {
        return _.map(
            this.instance().get_selected(true),
            _.property('original')
        );
    },

    /*
    select(node) {
    },
    */

    _destroy() {
        this.$el.jstree('destroy');
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
    },

    _triggerEvent(event) {
        this.trigger(`g:jstree:${event.type}`, this, event);
    }
});

export default TreeView;
