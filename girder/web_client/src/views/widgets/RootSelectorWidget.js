import _ from 'underscore';

import CollectionCollection from '@girder/core/collections/CollectionCollection';
import UserCollection from '@girder/core/collections/UserCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { getCurrentUser } from '@girder/core/auth';

import RootSelectorWidgetTemplate from '@girder/core/templates/widgets/rootSelectorWidget.pug';

/**
 * This widget creates a dropdown box allowing the user to select
 * "root" paths for a hierarchy widget.
 *
 * @emits RootSelectorWidget#g:selected The selected element changed
 * @type {object}
 * @property {Model|null} root The selected root model
 * @property {string|null} group The selection group
 *
 * @emits RootSelectorWidget#g:group A collection group was updated
 * @type {object}
 * @property {Collection} collection
 */
var RootSelectorWidget = View.extend({
    events: {
        'change #g-root-selector': '_selectRoot'
    },

    /**
     * Initialize the widget.  The caller can configure the list of items
     * that are present in the select box.  If no values are given, then
     * appropriate rest calls will be made to fetch models automatically.
     *
     * Additional categories of roots can be provided via an object mapping,
     * for example:
     *
     *   {
     *     friends: new UserCollection([...]),
     *     saved: new FolderCollection([...])
     *   }
     *
     * Only a single page of results are displayed for each collection provided.
     * The default maximum number can be configured, but for more sophisticated
     * behavior, the caller should act on the collection objects directly and
     * rerender.
     *
     * @param {object} settings
     * @param {UserModel} [settings.home=getCurrentUser()]
     * @param {object} [settings.groups] Additional collection groups to add
     * @param {number} [settings.pageLimit=25] The maximum number of models to fetch
     * @param {Model} [settings.selected] The default/current selection
     * @param {string[]} [settings.display=['Home', 'Collections', 'Users'] Display order
     * @param {boolean} [settings.reset=true] Always fetch from offset 0
     */
    initialize: function (settings) {
        settings = settings || {};

        this.pageLimit = settings.pageLimit || 25;

        // collections are provided for public access here
        this.groups = {
            'Collections': new CollectionCollection(),
            'Users': new UserCollection()
        };

        this.groups.Collections.pageLimit = settings.pageLimit;
        this.groups.Users.pageLimit = settings.pageLimit;
        this.groups.Users.sortField = 'login';

        // override default selection groups
        _.extend(this.groups, settings.groups);

        // attach collection change events
        _.each(this.groups, (group) => {
            this.listenTo(group, 'g:changed', () => {
                this._updateGroup(group);
            });
        });

        // possible values that determine rendered behavior for "Home":
        //   - model: show this model as Home
        //   - undefined|null: use getCurrentUser()
        this.home = settings.home;

        // we need to fetch the collections and rerender on login
        this.listenTo(events, 'g:login', this.fetch);

        this.selected = settings.selected;
        this.display = settings.display || ['Home', 'Collections', 'Users'];

        this.fetch();
    },

    render: function () {
        this._home = this.home || getCurrentUser();

        this.$el.html(
            RootSelectorWidgetTemplate({
                home: this._home,
                groups: this.groups,
                display: this.display,
                selected: this.selected,
                format: this._formatName
            })
        );

        return this;
    },

    /**
     * Called when the user selects a new item.  Resolves the
     * model object from the DOM and triggers the g:selected event.
     */
    _selectRoot: function (evt) {
        var sel = this.$(':selected');
        var id = sel.val();
        var group = sel.data('group') || null;
        this.selected = null;
        if (_.has(this.groups, group)) {
            this.selected = this.groups[group].get(id);
        } else if (this._home && this._home.id === id) {
            this.selected = this._home;
        }
        this.trigger('g:selected', {
            root: this.selected,
            group: group
        });
    },

    /**
     * Called when a collection is modified... rerenders the view.
     */
    _updateGroup: function (collection) {
        this.trigger('g:group', {
            collection: collection
        });
        this.render();
    },

    /**
     * Return a string to display for the given model.
     */
    _formatName: function (model) {
        var name = model.id;
        switch (model.get('_modelType')) {
            case 'user':
                name = model.get('login');
                break;
            case 'folder':
            case 'collection':
                name = model.get('name');
                break;
        }
        return name;
    },

    /**
     * Fetch all collections from the server.
     */
    fetch: function () {
        var reset = this.reset;
        _.each(this.groups, function (collection) {
            collection.fetch(null, reset);
        });
    }
});

export default RootSelectorWidget;
