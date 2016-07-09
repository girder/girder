/**
 * This widget provides the user with an interface similar to a filesystem
 * browser to pick a single user, collection, folder, or item from a
 * hierarchical view.
 */
girder.views.BrowserWidget = girder.View.extend({
    events: {
        'click .g-submit-button': '_submitButton'
    },

    initialize: function (settings) {
        settings = settings || {};
        this.title = settings.title || 'Select an item';
        this.validate = settings.validate || function () {};
        this.help = settings.help;
        this.showItems = settings.showItems;
        this._rootSelectionView = new girder.views.RootSelectorWidget({
            parentView: this,
            display: ['Collections', 'Users']
        });
        this.listenTo(this._rootSelectionView, 'g:selected', function (evt) {
            this._root = evt.root;
            this._renderHierarchyView();
        });
    },

    render: function () {
        this.$el.html(
            girder.templates.browserWidget({
                title: this.title,
                help: this.help
            })
        ).girderModal(this);
        this._renderRootSelection();
        return this;
    },

    _renderRootSelection: function () {
        this._rootSelectionView.setElement(this.$('.g-hierarchy-root-container')).render();
        this._renderHierarchyView();
    },

    _renderHierarchyView: function () {
        if (this._hierarchyView) {
            this.stopListening(this._hierarchyView);
            this._hierarchyView.off();
            this.$('.h-hierarchy-widget').empty();
        }
        if (!this._root) {
            return;
        }
        this.$('.g-wait-for-root').removeClass('hidden');
        this._hierarchyView = new girder.views.HierarchyWidget({
            parentView: this,
            parentModel: this._root,
            checkboxes: false,
            routing: false,
            showActions: false,
            showItems: this.showItems,
            onItemClick: _.bind(this._selectItem, this)
        });
        this.listenTo(this._hierarchyView, 'g:setCurrentModel', this._selectModel);
        this._hierarchyView.setElement(this.$('.g-hierarchy-widget-container')).render();
        this._selectModel();
    },

    _selectItem: function () {
    },

    _selectModel: function () {
        this.$('.g-validation-failed-message').addClass('hidden');
        this.$('.g-selected-model').removeClass('has-error');
        this.$('#g-selected-model').val(this._hierarchyView.parentModel.id);
    },

    _submitButton: function () {
        var model = this.selectedModel();
        var message = this.validate(model);
        if (message) {
            this.$('.g-selected-model').addClass('has-error');
            this.$('.g-validation-failed-message').removeClass('hidden').text(message);
        } else {
            this.$el.modal('hide');
            this.trigger('g:saved', model);
        }
    },

    selectedModel: function () {
        return this.$('#g-selected-model').val();
    }
});
