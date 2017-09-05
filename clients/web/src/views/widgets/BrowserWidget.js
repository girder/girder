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
     * @param {function} [validate] A validation function returning a promise that returns a string
        to be displayed on error, or undefined if valid.
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
     * @param {function} [input.validate] A validation function returning a promise that returns a
        string to be displayed on error, or undefined if valid.
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

    _submitButton: function () {
        this._validate();
    },

    /**
     * _validate independently validates the input-element and the selected-model.
     * The 4 possible outcomes of this validation are as follows...
     *
     * Case |  selected-model | input-element
     *  1.  |      Valid      |     Valid
     *  2.  |      Valid      |    Invalid
     *  3.  |     Invalid     |    Invalid
     *  4.  |     Invalid     |     Valid
     *
     * The code path for each case is commented inline
     */
    _validate: function () {
        var selectedModel = this.selectedModel();
        var invalidSelectedModel;
        var invalidInputElement;

        const validationPromise = $.Deferred().resolve()
            .then(() => {
                // Validate input-element
                if (this.input && this.input.validate) {
                    var message = this.input.validate(this.$('#g-input-element').val());
                    if (message === undefined) {
                        console.warn('Static validation is deprecated, return a promise instead');
                        return undefined;
                    } else if (_.isFunction(message.then)) {
                        return message;
                    } else {
                        throw message;
                    }
                } else {
                    return undefined;
                }
            })
            .then(() => {
                // input-element is valid
                // Validate selected-model
                var message = this.validate(selectedModel);
                if (message === undefined) {
                    console.warn('Static validation is deprecated, return a promise instead');
                    return undefined;
                } else if (_.isFunction(message.then)) {
                    return message;
                } else {
                    throw message;
                }
            }, (failMessage) => {
                // input-element is invalid
                invalidInputElement = failMessage;

                // Validate selected-model
                var message = this.validate(selectedModel);
                if (message === undefined) {
                    console.warn('Static validation is deprecated, return a promise instead');
                    return undefined;
                } else if (_.isFunction(message.then)) {
                    return message;
                } else {
                    throw message;
                }
            })
            .then(() => {
                // selected-model is valid
                if (invalidInputElement) {
                    // Case 2
                    return $.Deferred().reject().promise();
                } else {
                    // Case 1
                    return undefined;
                }
            }, (failMessage) => {
                // selected-model is invalid
                // Case 3 and 4
                invalidSelectedModel = failMessage;
                return $.Deferred().reject().promise();
            });

        $.when(validationPromise)
            .fail(() => {
                if (invalidInputElement) {
                    // Case 2 and 3
                    this.$('.g-input-element').addClass('has-error');
                    this.$('.g-validation-failed-message').removeClass('hidden').html(
                        _.escape(invalidInputElement) + '<br>' + _.escape(invalidSelectedModel));
                } else if (invalidSelectedModel) {
                    // Case 4
                    this.$('.g-selected-model').addClass('has-error');
                    this.$('.g-validation-failed-message').removeClass('hidden').text(invalidSelectedModel);
                }
            })
            .done(() => {
                // Case 1
                this.root = this._hierarchyView.parentModel;
                this.$el.modal('hide');
                this.trigger('g:saved', selectedModel, this.$('#g-input-element').val());
            });
    }
});

export default BrowserWidget;
