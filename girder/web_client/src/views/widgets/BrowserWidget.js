import _ from 'underscore';

import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import RootSelectorWidget from '@girder/core/views/widgets/RootSelectorWidget';
import View from '@girder/core/views/View';

import BrowserWidgetTemplate from '@girder/core/templates/widgets/browserWidget.pug';

import '@girder/core/stylesheets/widgets/browserWidget.styl';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This widget provides the user with an interface similar to a filesystem
 * browser to pick a single user, collection, folder, or item from a
 * hierarchical view.
 */
var BrowserWidget = View.extend({
    events: {
        'click .g-submit-button': function () {
            this._validate();
        }
    },

    /**
     * Initialize the widget.
     * @param {object} settings
     * @param {string} [titleText="Select an item"] Text to display in the modal header
     * @param {string} [helpText] Info text to display below the hierarchy widget
     * @param {string} [submitText="Save"] Text to display on the submit button
     * @param {boolean} [showItems=false] Show items in the hierarchy widget
     * @param {boolean} [showPreview=true] Show a preview of the current object id
     * @param {function} [validate] A validation function, which is passed the selected model as a
        parameter, and which should return a promise. The returned promise should resolve if the
        selection is acceptable and reject with a string value (as an error message) if the
        selection is unacceptable.
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
     * @param {function} [input.validate] A validation function, which is passed the value of the
        user-specified input element as a parameter, and which should return a promise. The returned
        promise should resolve if the selection is acceptable and reject with a string value (as an
        error message) if the selection is unacceptable.
     * @param {string} [input.placeholder] A placeholder string for the input element.
     */
    initialize: function (settings) {
        // store options
        settings = settings || {};
        this.titleText = settings.titleText || 'Select an item';
        this.validate = settings.validate || _.constant($.Deferred().resolve().promise());
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

    /**
     * Independently validate the input-element and the selected-model.
     */
    _validate: function () {
        // Validate input element
        let inputValidation;
        if (this.input && this.input.validate) {
            inputValidation = this.input.validate(this.$('#g-input-element').val());
            if (inputValidation === undefined) {
                console.warn('Static validation is deprecated, return a promise instead');
                inputValidation = $.Deferred().resolve().promise();
            } else if (!_.isFunction(inputValidation.then)) {
                console.warn('Static validation is deprecated, return a promise instead');
                inputValidation = $.Deferred().reject(inputValidation).promise();
            }
        } else {
            // No validator is implicit acceptance
            inputValidation = $.Deferred().resolve().promise();
        }

        // Validate selected element
        const selectedModel = this.selectedModel();
        let selectedValidation = this.validate(selectedModel);
        if (selectedValidation === undefined) {
            console.warn('Static validation is deprecated, return a promise instead');
            selectedValidation = $.Deferred().resolve().promise();
        } else if (!_.isFunction(selectedValidation.then)) {
            console.warn('Static validation is deprecated, return a promise instead');
            selectedValidation = $.Deferred().reject(selectedValidation).promise();
        }

        let invalidInputElement = null;
        let invalidSelectedModel = null;
        // We want to wait until both promises to run to completion, which only happens if they're
        // accepted. So, chain an extra handler on to them, which transforms a rejection into an
        // acceptance.
        $.when(
            inputValidation
                .catch((failMessage) => {
                    // input-element is invalid
                    invalidInputElement = failMessage;
                    return undefined;
                }),
            selectedValidation
                .catch((failMessage) => {
                    // selected-model is invalid
                    invalidSelectedModel = failMessage;
                    return undefined;
                })
        )
            .done(() => {
                // Reset any previous error states
                this.$('.g-selected-model').removeClass('has-error');
                this.$('.g-input-element').removeClass('has-error');
                this.$('.g-validation-failed-message').addClass('hidden').html('');

                // The 4 possible outcomes of this validation are as follows...
                //
                // Case |  input-element  |  selected-model
                //  1.  |      Valid      |      Valid
                //  2.  |      Valid      |     Invalid
                //  3.  |     Invalid     |      Valid
                //  4.  |     Invalid     |     Invalid
                if (!invalidInputElement && !invalidSelectedModel) {
                    // Case 1
                    this.root = this._hierarchyView.parentModel;
                    this.$el.modal('hide');
                    this.trigger('g:saved', selectedModel, this.$('#g-input-element').val());
                } else if (!invalidInputElement && invalidSelectedModel) {
                    // Case 2
                    this.$('.g-selected-model').addClass('has-error');
                    this.$('.g-validation-failed-message').removeClass('hidden').text(invalidSelectedModel);
                } else if (invalidInputElement && !invalidSelectedModel) {
                    // Case 3
                    this.$('.g-input-element').addClass('has-error');
                    this.$('.g-validation-failed-message').removeClass('hidden').text(invalidInputElement);
                } else if (invalidInputElement && invalidSelectedModel) {
                    // Case 4
                    this.$('.g-selected-model').addClass('has-error');
                    this.$('.g-input-element').addClass('has-error');
                    this.$('.g-validation-failed-message').removeClass('hidden').html(
                        _.escape(invalidInputElement) + '<br>' + _.escape(invalidSelectedModel));
                }
            });
    }
});

export default BrowserWidget;
