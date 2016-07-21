/**
 * This widget provides the user with an interface similar to a filesystem
 * browser to pick a single user, collection, folder, or item from a
 * hierarchical view.
 */
girder.views.BrowserWidget = girder.View.extend({
    events: {
        'click .g-submit-button': '_submitButton'
    },

    /**
     * Initialize the widget.
     * @param {object} settings
     * @param {string} [titleText="Select an item"] Text to display in the modal header
     * @param {string} [helpText] Info text to display below the hierarchy widget
     * @param {string} [submitText="Save"] Text to display on the submit button
     * @param {boolean} [showItems=false] Show items in the hierarchy widget
     * @param {boolean} [showPreview=true] Show a preview of the current object id
     * @param {function} [validate] A validation function returning a string that is displayed on error
     * @param {object} [rootSelectorSettings] Settings passed to the root selector widget
     */
    initialize: function (settings) {
        // store options
        settings = settings || {};
        this.titleText = settings.titleText || 'Select an item';
        this.validate = settings.validate || function () {};
        this.helpText = settings.helpText;
        this.showItems = settings.showItems;
        this.showPreview = settings.showPreview || true;
        this.submitText = settings.submitText || 'Save';

        // generate the root selection view and listen to it's events
        this._rootSelectionView = new girder.views.RootSelectorWidget(_.extend({
            parentView: this
        }, settings.rootSelectorSettings));
        this.listenTo(this._rootSelectionView, 'g:selected', function (evt) {
            this._root = evt.root;
            this._renderHierarchyView();
        });
    },

    render: function () {
        this.$el.html(
            girder.templates.browserWidget({
                title: this.titleText,
                help: this.helpText,
                preview: this.showPreview,
                submit: this.submitText
            })
        ).girderModal(this);
        this._renderRootSelection();
        return this;
    },

    /**
     * Return the selected model id.
     */
    selectedModel: function () {
        return this.$('#g-selected-model').val();
    },

    _renderRootSelection: function () {
        this._rootSelectionView.setElement(this.$('.g-hierarchy-root-container')).render();
        this._renderHierarchyView();
    },

    _renderHierarchyView: function () {
        if (this._hierarchyView) {
            this.stopListening(this._hierarchyView);
            this._hierarchyView.off();
            this.$('.g-hierarchy-widget-container').empty();
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
        // for future extensibility, do something when an item is clicked
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
    }
});
