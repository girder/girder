import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';
import BrowserWidget from 'girder/views/widgets/BrowserWidget';
import { getCurrentUser } from 'girder/auth';

import booleanWidget from '../templates/booleanWidget.pug';
import colorWidget from '../templates/colorWidget.pug';
import enumerationWidget from '../templates/enumerationWidget.pug';
import enumerationMultiWidget from '../templates/enumerationMultiWidget.pug';
import fileWidget from '../templates/fileWidget.pug';
import rangeWidget from '../templates/rangeWidget.pug';
import widget from '../templates/widget.pug';

import '../stylesheets/controlWidget.styl';
import 'bootstrap-colorpicker/dist/js/bootstrap-colorpicker';
import 'bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css';
import 'bootstrap-slider/dist/bootstrap-slider';
import 'bootstrap-slider/dist/css/bootstrap-slider.css';

var lastParent = null;

var ControlWidget = View.extend({
    events: {
        'change input,select': '_input',
        'changeColor': '_input',
        'click .g-select-file-button': '_selectFile'
    },

    initialize: function () {
        this.listenTo(this.model, 'change', this.change);
        this.listenTo(this.model, 'destroy', this.remove);
        this.listenTo(this.model, 'invalid', this.invalid);
        this.listenTo(events, 'g:itemTaskWidgetSet:' + this.model.id, (value) => {
            this.model.set('value', value);
        });
    },

    render: function (_, options) {
        this.$('.form-group').removeClass('has-error');
        this.model.isValid();
        if (options && options.norender) {
            return this;
        }
        this.$el.html(this.template()(this.model.attributes));
        this.$('.g-control-item[data-type="range"] input').slider();
        this.$('.g-control-item[data-type="color"] .input-group').colorpicker({});
        return this;
    },

    change: function () {
        this.render.apply(this, arguments);
        events.trigger('g:itemTaskWidgetChanged:' + this.model.get('type'), this.model);
        events.trigger('g:itemTaskWidgetChanged', this.model);
    },

    remove: function () {
        this.$('.g-control-item[data-type="color"] .input-group').colorpicker('destroy');
        this.$('.g-control-item[data-type="range"] input').slider('destroy');
        this.$el.empty();
        events.trigger('g:itemTaskWidgetRemoved:' + this.model.get('type'), this.model);
        events.trigger('g:itemTaskWidgetRemoved', this.model);
    },

    /**
     * Set classes on the input element to indicate to the user that the current value
     * is invalid.  This is automatically triggered by the model's "invalid" event.
     */
    invalid: function () {
        this.$('.form-group').addClass('has-error');
        events.trigger('g:itemTaskWidgetInvalid:' + this.model.get('type'), this.model);
        events.trigger('g:itemTaskWidgetInvalid', this.model);
    },

    /**
     * Type definitions mapping used internally.  Each widget type
     * specifies it's pug template and possibly more customizations
     * as needed.
     */
    _typedef: {
        range: {
            template: rangeWidget
        },
        color: {
            template: colorWidget
        },
        string: {
            template: widget
        },
        number: {
            template: widget
        },
        integer: {
            template: widget
        },
        boolean: {
            template: booleanWidget
        },
        'string-vector': {
            template: widget
        },
        'number-vector': {
            template: widget
        },
        'string-enumeration': {
            template: enumerationWidget
        },
        'string-enumeration-multiple': {
            template: enumerationMultiWidget
        },
        'number-enumeration': {
            template: enumerationWidget
        },
        'number-enumeration-multiple': {
            template: enumerationMultiWidget
        },
        file: {
            template: fileWidget
        },
        image: {
            template: fileWidget
        },
        directory: {
            template: fileWidget
        },
        'new-file': {
            template: fileWidget
        }
    },

    /**
     * Get the appropriate template for the model type.
     */
    template: function () {
        var type = this.model.get('type');
        var def = this._typedef[type];

        if (def === undefined) {
            console.warn('Invalid widget type "' + type + '"'); // eslint-disable-line no-console
            def = {};
        }
        return def.template || _.template('');
    },

    /**
     * Get the current value from an input (or select) element.
     */
    _input: function (evt) {
        var $el, val;

        $el = $(evt.target);
        val = $el.val();

        if ($el.attr('type') === 'checkbox') {
            val = $el.get(0).checked;
        }

        // we don't want to rerender, because this event is generated by the input element
        this.model.set('value', val, {norender: true});
    },

    /**
     * Get the value from a file selection modal and set the text in the widget's
     * input element.
     */
    _selectFile: function () {
        var showItems = false,
            input = false,
            preview = true,
            validate = _.noop,
            type = this.model.get('type'),
            title, help;

        // Customize the browser widget according the argument type
        if (type === 'file' || type === 'image') {
            showItems = true;
            title = 'Select an item';
            help = 'Click on an item to select it, then click "Save"';
        }

        if (type === 'directory') {
            title = 'Select a folder';
            help = 'Browse to a directory to select it, then click "Save"';
        }

        if (type === 'new-file') {
            title = 'Create a new item';
            help = 'Browse to a path, enter a name, then click "Save"';
            input = {
                label: 'Name',
                placeholder: 'Choose a name for the new item',
                validate: (val) => {
                    // validation on the "new item name"
                    if (!val) {
                        return 'Please provide an item name.';
                    }
                },
                default: this.model.get('fileName')
            };
            // validation on the parent model
            validate = (model) => {
                var type = model.get('_modelType');
                if (type !== 'folder') {
                    return 'Invalid parent type, please choose a folder.';
                }
            };
            preview = false;
        }

        var modal = new BrowserWidget({
            el: $('#g-dialog-container'),
            parentView: this,
            showItems: showItems,
            selectItem: showItems,
            root: lastParent || getCurrentUser(),
            titleText: title,
            helpText: help,
            input: input,
            showPreview: preview,
            validate: validate
        });
        modal.once('g:saved', (model, inputValue) => {
            lastParent = modal.root;
            modal.$el.modal('hide');
            this.model.set({
                value: model,
                fileName: inputValue || model.name()
            });
        }).render();
    }
});

export default ControlWidget;
