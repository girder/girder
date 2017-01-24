import _ from 'underscore';

/**
 * Convert from a string to the given value type.
 * @param {string} type A widget type
 * @param {string} value The value to be converted
 * @returns {*} The converted value
 */
function convert(type, value) {
    if (type === 'number' || type === 'number-enumeration') {
        value = parseFloat(value);
    } else if (type === 'boolean') {
        value = (value.toLowerCase() === 'true');
    } else if (type === 'number-vector') {
        value = _.map(value.split(','), parseFloat);
    } else if (type === 'string-vector') {
        value = value.split(',');
    }
    return value;
}

export default convert;
