import convert from './convert';

/**
 * Parse a `default` tag returning an empty object when no default is given.
 */
function defaultValue(type, value) {
    var output = {};
    if (value.length) {
        output = {value: convert(type, value.text())};
    }
    return output;
}

export default defaultValue;
