import _ from 'underscore';

import { AccessType } from '@girder/core/constants';
import events from '@girder/core/events';
import View from '@girder/core/views/View';

import ItemTagsWidgetTemplate from '../templates/itemTagsWidget.pug';
import ItemTagWidgetTemplate from '../templates/itemTagWidget.pug';
import ItemTagAutocompleteMenuTemplate from '../templates/itemTagAutocompleteMenu.pug';

import 'bootstrap/js/dropdown';

import '../stylesheets/itemTagsWidget.styl';

/**
 * A widget for rendering a single item tag.
 */
const ItemTagWidget = View.extend({
    className: 'g-widget-item-tags-row',
    events: {
        'click .g-widget-item-tags-edit-button': 'editTag',
        'click .g-widget-item-tags-cancel-button': 'cancelTag',
        'click .g-widget-item-tags-save-button': 'saveTag',
        'click .g-widget-item-tags-delete-button': 'deleteTag',
        'keyup .g-widget-item-tags-tag-input': function (event) {
            if (event.key === 'Enter') {
                if (this.highlightIndex >= 0) {
                    // an autocomplete option is highlighted, select it instead of saving
                    const tag = this.$el.find('.g-widget-item-tags-autocomplete-option.selected').attr('data-tag');
                    this.$el.find('.g-widget-item-tags-tag-input').val(tag);
                    this.highlightIndex = -1;
                    this.updateAutocomplete();
                } else {
                    this.saveTag();
                }
            } else {
                if (event.key === 'ArrowUp') {
                    this.highlightIndex--;
                } else if (event.key === 'ArrowDown') {
                    this.highlightIndex++;
                } else {
                    // any non arrow key events will remove the autocomplete option highlight
                    this.highlightIndex = -1;
                }
                this.updateAutocomplete();
            }
        },
        'focusin .g-widget-item-tags-tag-input': 'showAutocomplete',
        'focusout .g-widget-item-tags-tag-input': 'hideAutocomplete',
        'mousedown .g-widget-item-tags-autocomplete-option': 'selectAutocompleteOption'
    },
    initialize: function (settings) {
        this.tag = settings.tag;
        this.index = settings.index;
        this.accessLevel = settings.accessLevel;
        this.parentView = settings.parentView;
        this.onItemSaved = settings.onItemSaved;
        this.onItemDeleted = settings.onItemDeleted;
        this.editing = settings.editing || false;
        this.highlightIndex = -1; // -1 means no autocomplete option selected
    },
    render: function () {
        this.$el.html(ItemTagWidgetTemplate({
            tag: this.tag,
            editing: this.editing,
            accessLevel: this.accessLevel,
            AccessType: AccessType
        }));
        if (this.editing) {
            this.updateAutocomplete();
        }
        return this;
    },
    editTag: function () {
        this.editing = true;
        this.render();
        this.$el.find('.g-widget-item-tags-tag-input').focus();
    },
    cancelTag: function () {
        this.editing = false;
        this.render();
    },
    saveTag: function () {
        this.onItemSaved(this.index, this.$el.find('.g-widget-item-tags-tag-input').val());
    },
    deleteTag: function () {
        this.onItemDeleted(this.index, this.tag);
    },
    /** Updates the autocomplete options, including highlighting */
    updateAutocomplete: function () {
        const input = this.$el.find('.g-widget-item-tags-tag-input');
        if (input === '') {
            return;
        }
        if (this.parentView.allowedTags !== null) {
            const autocompleteOptions = this.parentView.allowedTags.filter(function (tag) {
                return tag.startsWith(input.val());
            }).slice(0, 10);
            if (this.highlightIndex < -1) {
            // user must have wrapped around, change the highlight to the end of the array
                this.highlightIndex = autocompleteOptions.length - 1;
            }
            if (this.highlightIndex >= autocompleteOptions.length) {
            // user must have gone off the end of the list, change highlight back to -1 (no option selected)
                this.highlightIndex = -1;
            }
            this.$el.find('.g-widget-item-tags-autocomplete-menu .dropdown-menu').html(ItemTagAutocompleteMenuTemplate({
                autocompleteOptions: autocompleteOptions,
                highlightIndex: this.highlightIndex
            }));
            this.showAutocomplete();
        }
    },
    /** Show the autocomplete dropdown if autocomplete is possible */
    showAutocomplete: function () {
        if (this.parentView.allowedTags !== null) {
            this.$el.find('.dropdown').addClass('open');
        }
    },
    /** Hide the autocomplete dropdown */
    hideAutocomplete: function () {
        this.$el.find('.dropdown').removeClass('open');
    },
    /** Handles click events on the autocomplete dropdown options */
    selectAutocompleteOption: function (event) {
        this.$el.find('.g-widget-item-tags-tag-input').val(event.target.getAttribute('data-tag'));
        this.updateAutocomplete();
    }
});

/**
 * A widget for displaying a list of item tags.
 */
const ItemTagsWidget = View.extend({
    events: {
        'click .g-widget-item-tags-add-button': 'addItemTag'
    },
    initialize: function (settings) {
        this.tags = settings.tags;
        this.accessLevel = settings.accessLevel;
        this.saveTags = settings.saveTags;
        this.allowedTags = settings.allowedTags;
        this.render();
    },
    render: function () {
        this.$el.html(ItemTagsWidgetTemplate({
            accessLevel: this.accessLevel,
            AccessType: AccessType
        }));
        _.each(this.tags, function (tag, index) {
            this.$el.find('.g-widget-item-tags-container').append(new ItemTagWidget({
                tag: tag,
                index: index,
                accessLevel: this.accessLevel,
                parentView: this,
                onItemSaved: this.itemSaved.bind(this),
                onItemDeleted: this.itemDeleted.bind(this),
                editing: tag === '' // new tags start empty, they should be initially editable
            }).render().$el);
        }, this);
        return this;
    },
    addItemTag: function () {
        if (!this.tags.includes('')) {
            this.tags.push('');
            this.render();
        }
        $('.g-widget-item-tags-tag-input').last().focus();
    },
    /** Passed to ItemTagWidget and called when a tag being edited is saved */
    itemSaved: function (index, tag) {
        this.tags[index] = tag;
        if (this.validateTags()) {
            this.saveTags(this.tags);
        }
    },
    /** Passed to ItemTagWidget and called when a tag being edited is deleted */
    itemDeleted: function (index, tag) {
        this.tags.splice(index, 1);
        this.saveTags();
    },
    /** Validates that the current list of tags is a subset of allowedTags */
    validateTags: function () {
        if (this.allowedTags === null) {
            return true;
        }

        var failedValidation = false;
        for (const tag of this.tags) {
            if (!this.allowedTags.includes(tag)) {
                events.trigger('g:alert', {
                    text: `Tag "${tag}" is not defined`,
                    type: 'danger'
                });
                failedValidation = true;
            }
        }
        return !failedValidation;
    }
});

export default ItemTagsWidget;
