import _ from 'underscore';

import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import RootSelectorWidget from 'girder/views/widgets/RootSelectorWidget';
import View from 'girder/views/View';

import BrowserWidgetTemplate from 'girder/templates/widgets/browserWidget.pug';

import 'girder/stylesheets/widgets/browserWidget.styl';
import 'girder/utilities/jquery/girderModal';

/**
 * This widget provides the user with an interface similar to a filesystem
 * browser to pick a single user, collection, folder, or item from a
 * hierarchical view.
 */
var BrowserWidget = View.extend({
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
     * @param {boolean} [showMetadata=false] Show the metadata editor inside the hierarchy widget
     * @param {Model} [root] The default root model to pass to the hierarchy widget
     * @param {boolean} [selectItem=false] Adjust behavior to enable selecting items rather
     *   than folders. This will add a handler to the hierarchy widget responding to
     *   clicks on items to select a target rather than inferring it from the browsed
     *   location.
     * @param {object} [input=false] Settings passed to an optional text input box
     *   The input box is primarily meant to be for a user to enter a file name
     *   as in a "Save As" dialog.  The default (false) hides this element.
     * @param {string} [input.label="Name"] A label for the input element.
     * @param {string} [input.default] The default value
     * @param {function} [input.validate] A validation function.  This function
     *   accepts the user input as an argument and should return "undefined"
     *   for a valid value or a string to pass to the user for an invalid value.
     * @param {string} [input.placeholder] A placeholder string for the input element.
     */
    initialize: function (settings) {
        // store options
        settings = settings || {};
        this.titleText = settings.titleText || 'Select an item';
        this.validate = settings.validate || function () {};
        this.helpText = settings.helpText;
        this.showItems = settings.showItems;
        this.showPreview = _.isUndefined(settings.showPreview) ? true : !!settings.showPreview;
        this.submitText = settings.submitText || 'Save';
        this.root = settings.root;
        this.input = settings.input;
        this.selectItem = !!settings.selectItem;
        this.showMetadata = !!settings.showMetadata;
        this._selected = null;

        // generate the root selection view and listen to it's events
        this._rootSelectionView = new RootSelectorWidget(_.extend({
            parentView: this
        }, settings.rootSelectorSettings));
        this.listenTo(this._rootSelectionView, 'g:selected', function (evt) {
            this.root = evt.root;
            this._renderHierarchyView();
        });
    },

    render: function () {
        this.$el.html(
            BrowserWidgetTemplate({
                title: this.titleText,
                help: this.helpText,
                preview: this.showPreview,
                submit: this.submitText,
                input: this.input,
                selectItem: this.selectItem
            })
        ).girderModal(this);
        this._renderRootSelection();
        return this;
    },

    /**
     * Return the selected model.
     */
    selectedModel: function () {
        return this._selected;
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
        if (!this.root) {
            return;
        }
        this.$('.g-wait-for-root').removeClass('hidden');
        this._hierarchyView = new HierarchyWidget({
            el: this.$('.g-hierarchy-widget-container'),
            parentView: this,
            parentModel: this.root,
            checkboxes: false,
            routing: false,
            showActions: false,
            showItems: this.showItems,
            onItemClick: _.bind(this._selectItem, this),
            showMetadata: this.showMetadata
        });
        this.listenTo(this._hierarchyView, 'g:setCurrentModel', this._selectModel);
        this._selectModel();
    },

    _resetSelection: function (model) {
        this._selected = model;
        this.$('.g-validation-failed-message').addClass('hidden');
        this.$('.g-selected-model').removeClass('has-error');
        this.$('.g-input-element').removeClass('has-error');
        this.$('#g-selected-model').val('');
        if (this._selected) {
            this.$('#g-selected-model').val(this._selected.get('name'));
        }
    },

    _selectItem: function (item) {
        if (!this.selectItem) {
            return;
        }
        this._resetSelection(item);
    },

    _selectModel: function () {
        if (this.selectItem) {
            return;
        }
        this._resetSelection(this._hierarchyView.parentModel);
    },

    _submitButton: function () {
        var model = this.selectedModel();
        var message = this.validate(model);
        var inputMessage;

        if (this.input && this.input.validate) {
            inputMessage = this.input.validate(this.$('#g-input-element').val());
        }

        if (inputMessage) {
            this.$('.g-input-element').addClass('has-error');
            this.$('.g-validation-failed-message').removeClass('hidden').html(
                _.escape(inputMessage) + '<br>' + _.escape(message)
            );
        } else if (message) {
            this.$('.g-selected-model').addClass('has-error');
            this.$('.g-validation-failed-message').removeClass('hidden').text(message);
        } else {
            this.root = this._hierarchyView.parentModel;
            this.$el.modal('hide');
            this.trigger('g:saved', model, this.$('#g-input-element').val());
        }
    }
});

export default BrowserWidget;
