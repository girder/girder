/**
 * Convert from a string to the given value type.
 * @param {string} type A widget type
 * @param {string} value The value to be converted
 * @returns {*} The converted value
 */
export default function convert(type, value) {
    if (type === 'number' || type === 'number-enumeration') {
        value = parseFloat(value);
    } else if (type === 'boolean') {
        value = (value.toLowerCase() === 'true');
    } else if (type === 'number-vector') {
        value = value.split(',').map(parseFloat);
    } else if (type === 'string-vector') {
        value = value.split(',');
    }
    return value;
}
