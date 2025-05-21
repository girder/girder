import tinycolor from 'tinycolor2';

const _ = girder._;
const Backbone = girder.Backbone;

/**
 * A backbone model controlling the behavior and rendering of widgets.
 */
const WidgetModel = Backbone.Model.extend({
    defaults: {
        type: '', // The specific widget type
        title: '', // The label to display with the widget
        description: '', // The description to display with the widget
        value: '', // The current value of the widget

        values: [] // A list of possible values for enum types

        // optional attributes only used for certain widget types
        /*
        parent: {},        // A parent girder model
        path: [],          // The path of a girder model in a folder hierarchy
        min: undefined,    // A minimum value
        max: undefined,    // A maximum value
        step: 1            // Discrete value intervals
        */
    },

    /**
     * Sets initial model attributes with normalization.
     */
    initialize(model) {
        this.set(_.defaults(model || {}, this.defaults));
    },

    /**
     * Override Model.set for widget specific behavior.
     */
    set(hash, options) {
        let key, value;

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
                hash.values = _.map(hash.values, _.bind(this.normalize, this));
            } catch (e) {
                console.warn('Could not normalize value in "' + hash.values + '"'); // eslint-disable-line no-console
            }
        }

        return Backbone.Model.prototype.set.call(this, hash, options);
    },

    /**
     * Coerce a value into a normalized native type.
     */
    normalize(value) {
        if (this.isVector()) {
            return this._normalizeVector(value);
        }
        return this._normalizeValue(value);
    },

    /**
     * Coerce a vector of values into normalized native types.
     */
    _normalizeVector(value) {
        if (value === '') {
            value = [];
        } else if (_.isString(value)) {
            value = value.split(',');
        }
        return value.map((v) => this._normalizeValue(v));
    },

    _normalizeValue(value) {
        if (this.isNumeric()) {
            value = parseFloat(value);
        } else if (this.isInteger()) {
            value = parseInt(value);
        } else if (this.isBoolean()) {
            value = !!value;
        } else if (this.isColor()) {
            if (Array.isArray(value)) {
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
    validate(model) {
        if (!_.contains(this.types, model.type)) {
            return 'Invalid type, "' + model.type + '"';
        }

        if (this.isVector()) {
            return this._validateVector(model.value);
        } else if (this.isGirderModel()) {
            return this._validateGirderModel(model);
        }
        return this._validateValue(model.value);
    },

    /**
     * Validate a potential value for the current widget type and properties.
     * This method is called once for each component for vector types.
     */
    _validateValue(value) {
        let out;
        if (this.isNumeric()) {
            out = this._validateNumeric(value);
        } else if (this.isInteger()) {
            out = this._validateInteger(value);
        }
        if (this.isEnumeration() && !_.contains(this.get('values'), this.normalize(value))) {
            out = 'Invalid value choice';
        }
        return out;
    },

    /**
     * Validate a potential vector value.  Calls _validateValue internally.
     */
    _validateVector(vector) {
        vector = this.normalize(vector);

        let val = _.chain(vector)
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
    _validateNumeric(value) {
        let min = parseFloat(this.get('min'));
        const max = parseFloat(this.get('max'));
        const step = parseFloat(this.get('step'));
        const eps = 1e-6;

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
        const mod = (value - min) / (step || 1);
        if (step > 0 && Math.abs(Math.round(mod) - mod) > eps) {
            return 'Value does not satisfy step "' + step + '"';
        }
    },

    /**
     * Validate an integral value.
     * @param {*} value The value to validate
     * @returns {undefined|string} An error message or undefined
     */
    _validateInteger(value) {
        let min = parseInt(this.get('min'));
        const max = parseInt(this.get('max'));
        const step = parseInt(this.get('step'));

        // make sure it is a valid number
        if (!isFinite(value)) {
            return `Invalid integer "${value}"`;
        }

        // make sure it is in valid range
        if (value < min || value > max) {
            return `Value out of range [${min}, ${max}]]`;
        }

        // make sure value is approximately an integer number
        // of "steps" larger than "min"
        min = min || 0;
        if (step > 0 && ((value - min) % (step || 1))) {
            return `Value does not satisfy step "${step}"`;
        }
    },

    /**
     * Validate a widget that selects a girder model.
     * @note This method is synchronous, so it cannot validate
     * the model on the server.
     */
    _validateGirderModel(model) {
        if (!model.value || !model.value.get('name')) {
            if (!this.get('required')) {
                return;
            }
            return 'Empty value';
        }

        switch (this.get('type')) {
            case 'new-file':
                if (!model.parent || model.parent.resourceName !== 'folder') {
                    return 'Invalid parent model';
                }
                break;
            // other model types...
        }
    },

    /**
     * True if the value should be coerced as a number.
     */
    isNumeric() {
        return _.contains(
            ['range', 'number', 'number-vector', 'number-enumeration', 'region'],
            this.get('type')
        );
    },

    /**
     * True if the value should be coerced as an integer.
     */
    isInteger() {
        return this.get('type') === 'integer';
    },

    /**
     * True if the value should be coerced as a boolean.
     */
    isBoolean() {
        return this.get('type') === 'boolean';
    },

    /**
     * True if the value is a 3 component vector.
     */
    isVector() {
        return _.contains(
            ['number-vector', 'string-vector', 'region'],
            this.get('type')
        );
    },

    /**
     * True if the value should be coerced as a color.
     */
    isColor() {
        return this.get('type') === 'color';
    },

    /**
     * True if the value should be chosen from one of several "values".
     */
    isEnumeration() {
        return _.contains(
            ['number-enumeration', 'string-enumeration'],
            this.get('type')
        );
    },

    /**
     * True if the value represents a model stored in a girder
     * collection/folder/item hierarchy.
     */
    isGirderModel() {
        return _.contains(
            ['directory', 'file', 'item', 'new-file', 'image', 'multi'],
            this.get('type')
        );
    },

    /**
     * True if the value represents a file stored in girder.
     */
    isFile() {
        return this.get('type') === 'file';
    },

    /**
     * True if the value represents an item stored in girder.
     */
    isItem() {
        return this.get('type') === 'item';
    },

    /**
     * Get a normalized representation of the widget's value.
     */
    value() {
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
        'string-enumeration',
        'file',
        'item',
        'directory',
        'multi',
        'new-file',
        'image',
        'region'
    ]
});

export default WidgetModel;
