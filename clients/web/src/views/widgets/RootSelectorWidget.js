/**
 * This widget creates a dropdown box allowing the user to select
 * "root" paths for a hierarchy widget.
 *
 * @emits RootSelectorWidget#g:selected The selected element changed
 * @type {object}
 * @property {girder.Model|null} root The selected root model
 * @property {string|null} group The selection group
 *
 * @emits RootSelectorWidget#g:group A collection group was updated
 * @type {object}
 * @property {girder.Collection} collection
 */
girder.views.RootSelectorWidget = girder.View.extend({
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
     *     friends: new girder.collections.UserCollection([...]),
     *     saved: new girder.collections.FolderCollection([...])
     *   }
     *
     * Only a single page of results are displayed for each collection provided.
     * The default maximum number can be configured, but for more sophisticated
     * behavior, the caller should act on the collection objects directly and
     * rerender.
     *
     * @param {object} settings
     * @param {girder.models.UserModel} [settings.home=girder.currentUser]
     * @param {object} [settings.groups] Additional collection groups to add
     * @param {number} [settings.pageLimit=25] The maximum number of models to fetch
     * @param {girder.Model} [settings.selected] The default/current selection
     * @param {string[]} [settings.display=['Home', 'Collections', 'Users'] Display order
     * @param {boolean} [settings.reset=true] Always fetch from offset 0
     */
    initialize: function (settings) {
        settings = settings || {};

        this.pageLimit = settings.pageLimit || 25;

        // collections are provided for public access here
        this.groups = {
            'Collections': new girder.collections.CollectionCollection(),
            'Users': new girder.collections.UserCollection()
        };

        this.groups.Collections.pageLimit = settings.pageLimit;
        this.groups.Users.pageLimit = settings.pageLimit;
        this.groups.Users.sortField = 'login';

        // override default selection groups
        _.extend(this.groups, settings.groups);

        // attach collection change events
        _.each(this.groups, _.bind(function (group) {
            this.listenTo(group, 'g:changed', this._updateGroup);
        }, this));

        // possible values that determine rendered behavior for "Home":
        //   - model: show this model as Home
        //   - undefined|null: use girder.currentUser
        this.home = settings.home;

        // we need to fetch the collections and rerender on login
        this.listenTo(girder.events, 'g:login', this.fetch);

        this.selected = settings.selected;
        this.display = settings.display || ['Home', 'Collections', 'Users'];

        this.fetch();
    },

    render: function () {
        this._home = this.home || girder.currentUser;

        this.$el.html(
            girder.templates.rootSelectorWidget({
                home: this._home,
                groups: this.groups,
                display: this.display,
                selected: this.selected,
                format: this._formatName
            })
        );
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
     * Called when a collections was modified.  Rerenders the view.
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
