import _ from 'underscore';
import Backbone from 'backbone';
import tinycolor from 'tinycolor2';

/**
 * A backbone model controlling the behavior and rendering of widgets.
 * This model and the corresponding views provide UI elements to
 * prompt the user for input.  Several different kinds of widgets
 * are available:
 *
 * Primitive types:
 *   * color:
 *      a color picker
 *   * range:
 *      a slider for choosing a numeric value within some range
 *   * number:
 *      an input box that accepts arbitrary numbers
 *   * boolean:
 *      a checkbox
 *   * string:
 *      an input element that accepts arbitrary strings
 *   * integer:
 *      an input box that accepts integers
 *   * number-vector:
 *      an input box that accepts a comma seperated list of numbers
 *   * string-vector:
 *      an input box that accepts a comma seperated list of strings
 *   * number-enumeration:
 *      a select box containing numbers
 *   * number-enumeration-multiple:
 *      a multiselect box containing numbers
 *   * string-enumeration:
 *      a select box containing strings
 *   * string-enumeration-multiple:
 *      a multiselect box containing strings
 *   * region
 *      a numeric vector type representing a subregion of an image
 *
 * Girder models:
 *   * file:
 *      an input file (evaluates to an item id)
 *   * directory:
 *      an input folder (evaluates to a folder id)
 *   * new-file:
 *      an output file (contains an existing folder id and a
 *      name that will be used for the new item.
 *   * new-folder:
 *      an output folder (contains a folder id and a
 *      name that will be used for the new folder.
 *   * image:
 *      an alias for the "file" type that expects the file
 *      contents is an image (this is not validated)
 *
 * @param {object} [attrs]
 * @param {string} [attrs.type]
 *   The widget type.  See the list of supported types.
 *
 * @param {string} [attrs.title]
 *   The label of the widget displayed to the user.  Falls back
 *   to `attrs.name` or `attrs.id` if not provided.
 *
 * @param {string} [attrs.description]
 *   A brief description of the parameter provided to the user.
 *
 * @param {object} [attrs.default]
 *   The fallback value if attrs.value is not set.  Primitive
 *   types expect this object to contain a "data" key whose
 *   value is the default.
 *
 * @param {*} [attrs.value]
 *   The current value of the widget.  Watch changes to this
 *   attribute to respond to user selections.
 *
 * @param {array} [attrs.values]
 *   The set of possible values for an enumerated type.  This
 *   is used to fill in the options presented in a dropdown box.
 *
 * @param {number} [attrs.min]
 *   The minimum value allowed for a numeric value.
 *
 * @param {number} [attrs.max]
 *   The maximum value allowed for a numeric value.
 *
 * @param {number} [attrs.step]
 *   The resolution of allowed numeric values.  This
 *   value determines the "ticks" in the number slider.
 *
 * @param {string} [attrs.fileName]
 *   For output files, this is the name used for the new file.
 */
var WidgetModel = Backbone.Model.extend({
    /**
     * Sets initial model attributes with normalization.
     */
    initialize: function (attrs) {
        attrs = attrs || {};

        _.defaults(attrs, {
            title: attrs.name || attrs.id,
            id: attrs.name,
            description: ''
        });

        if (!_.has(attrs, 'value') &&
            _.has(attrs.default || {}, 'data')) {
            attrs.value = attrs.default.data;
        }

        /*
         * Integers are special numeric types where adjacent values differ
         * by exactly 1.  Setting the "step" field to one, ensures that
         * clicking the input element arrows increment or decrement the
         * value by one.
         */
        if (attrs.type === 'integer') {
            attrs.step = 1;

            if (_.has(attrs, 'min')) {
                /*
                 * Ensure the minimum value is an integer for correct
                 * validation and input element behavior.
                 */
                attrs.min = Math.ceil(attrs.min);
            }
        }
        this.set(attrs);
    },

    /**
     * Override Model.set for widget specific bahavior.
     */
    set: function (hash, options) {
        var key, value;

        // handle set(key, value) calling
        if (_.isString(hash)) {
            key = hash;
            value = options;
            options = arguments[2];
            hash = {};
            hash[key] = value;
        }

        // normalize values
        if (_.has(hash, 'value')) {
            try {
                hash.value = this.normalize(hash.value);
            } catch (e) {
                console.warn('Could not normalize value "' + hash.value + '"'); // eslint-disable-line no-console
            }
        }

        // normalize enumerated values
        if (_.has(hash, 'values')) {
            try {
                hash.values = _.map(hash.values, _.bind(this._normalizeValue, this));
            } catch (e) {
                console.warn('Could not normalize value in "' + hash.values + '"'); // eslint-disable-line no-console
            }
        }

        return Backbone.Model.prototype.set.call(this, hash, options);
    },

    /**
     * Coerce a value into a normalized native type.
     */
    normalize: function (value) {
        if (this.isVector()) {
            return this._normalizeVector(value);
        }
        return this._normalizeValue(value);
    },

    /**
     * Coerce a vector of values into normalized native types.
     */
    _normalizeVector: function (value) {
        if (value === '') {
            value = [];
        } else if (_.isString(value)) {
            value = value.split(',');
        }
        return _.map(value, _.bind(this._normalizeValue, this));
    },

    _normalizeValue: function (value) {
        if (this.isNumeric()) {
            value = parseFloat(value);
        } else if (this.isInteger()) {
            value = parseInt(value);
        } else if (this.isBoolean()) {
            value = !!value;
        } else if (this.isColor()) {
            if (_.isArray(value)) {
                value = {r: value[0], g: value[1], b: value[2]};
            }
            value = tinycolor(value).toHexString();
        } else if (!this.isGirderModel()) {
            value = value.toString();
        }
        return value;
    },

    /**
     * Validate the model attributes.  Returns undefined upon successful validation.
     */
    validate: function (model) {
        if (!_.contains(this.types, model.type)) {
            return 'Invalid type, "' + model.type + '"';
        }

        if (this.isVector()) {
            return this._validateVector(model.value);
        } else if (model.type === 'new-file') {
            return this._validateGirderModel(model.value) ||
                (model.fileName ? undefined : 'No file name provided');
        } else if (model.type === 'new-folder') {
            return this._validateGirderModel(model.value) ||
                (model.fileName ? undefined : 'No folder name provided');
        } else if (this.isGirderModel()) {
            return this._validateGirderModel(model.value);
        }
        return this._validateValue(model.value);
    },

    /**
     * Validate a potential value for the current widget type and properties.
     * This method is called once for each component for vector types.
     */
    _validateValue: function (value) {
        var out;
        if (this.isNumeric()) {
            out = this._validateNumeric(value);
        }
        if (this.isEnumeration() && !_.contains(this.get('values'), this._normalizeValue(value))) {
            out = 'Invalid value choice';
        }
        return out;
    },

    /**
     * Validate a potential vector value.  Calls _validateValue internally.
     */
    _validateVector: function (vector) {
        var val;
        vector = this.normalize(vector);

        val = _.chain(vector)
            .map(_.bind(this._validateValue, this))
            .reject(_.isUndefined)
            .value();

        if (val.length === 0) {
            // all components validated
            val = undefined;
        } else {
            // join errors in individual components
            val = val.join('\n');
        }
        return val;
    },

    /**
     * Validate a numeric value.
     * @param {*} value The value to validate
     * @returns {undefined|string} An error message or null
     */
    _validateNumeric: function (value) {
        var min = parseFloat(this.get('min'));
        var max = parseFloat(this.get('max'));
        var step = parseFloat(this.get('step'));
        var mod, eps = 1e-6;

        // make sure it is a valid number
        if (!isFinite(value)) {
            return 'Invalid number "' + value + '"';
        }

        // make sure it is in valid range
        if (value < min || value > max) {
            return 'Value out of range [' + [min, max] + ']';
        }

        // make sure value is approximately an integer number
        // of "steps" larger than "min"
        min = min || 0;
        mod = (value - min) / step;
        if (step > 0 && Math.abs(Math.round(mod) - mod) > eps) {
            return 'Value does not satisfy step "' + step + '"';
        }
    },

    /**
     * Validate a widget that selects a girder model.
     * @note This method is synchronous, so it cannot validate
     * the model on the server.
     */
    _validateGirderModel: function (model) {
        var type = model && model.get && model.get('_modelType');
        if (!model) {
            return 'Empty value';
        } else if (!type) {
            return 'Invalid value';
        } else if (this.get('type') === 'file' && type !== 'item') {
            return 'Value must be an item';
        } else if (this.get('type') === 'image' && type !== 'item') {
            return 'Value must be an item';
        } else if (this.get('type') === 'directory' && type !== 'folder') {
            return 'Value must be a folder';
        } else if (this.get('type') === 'new-file' && type !== 'folder') {
            return 'Value must be a folder';
        } else if (this.get('type') === 'new-folder' && !_.contains(['folder', 'collection', 'user'], type)) {
            return 'Value must be a collection, folder, or user';
        }
    },

    /**
     * True if the value should be coerced as a number.
     */
    isNumeric: function () {
        return _.contains([
            'range',
            'integer',
            'number',
            'number-vector',
            'number-enumeration',
            'number-enumeration-multiple',
            'region'
        ], this.get('type'));
    },

    /**
     * True if the value should be coerced as an integer.
     */
    isInteger: function () {
        return this.get('type') === 'integer';
    },

    /**
     * True if the value should be coerced as a boolean.
     */
    isBoolean: function () {
        return this.get('type') === 'boolean';
    },

    /**
     * True if the value is a 3 component vector.
     */
    isVector: function () {
        return _.contains([
            'number-vector',
            'number-enumeration-multiple',
            'string-vector',
            'string-enumeration-multiple',
            'region'
        ], this.get('type'));
    },

    /**
     * True if the value should be coerced as a color.
     */
    isColor: function () {
        return this.get('type') === 'color';
    },

    /**
     * True if the value should be chosen from one of several "values".
     */
    isEnumeration: function () {
        return _.contains([
            'number-enumeration',
            'number-enumeration-multiple',
            'string-enumeration',
            'string-enumeration-multiple'
        ], this.get('type'));
    },

    /**
     * True if the value represents a model stored in a girder
     * collection/folder/item hierarchy.
     */
    isGirderModel: function () {
        return _.contains(
            ['directory', 'new-folder', 'file', 'new-file', 'image'],
            this.get('type')
        );
    },

    /**
     * True if the value represents a file stored in girder.
     */
    isFile: function () {
        return this.get('type') === 'file';
    },

    /**
     * Get a normalized representation of the widget's value.
     */
    value: function () {
        return this.get('value');
    },

    /**
     * A list of valid widget types.
     */
    types: [
        'color',
        'range',
        'number',
        'boolean',
        'string',
        'integer',
        'number-vector',
        'string-vector',
        'number-enumeration',
        'number-enumeration-multiple',
        'string-enumeration',
        'string-enumeration-multiple',
        'file',
        'directory',
        'new-file',
        'new-folder',
        'image',
        'region'
    ]
});

export default WidgetModel;
