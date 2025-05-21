import convert from './convert';

/**
 * Parse a `default` tag returning an empty object when no default is given.
 * If the default value appears to be a templated string, also return an
 * empty object.
 */
export default function defaultValue(type, value) {
    if (value.length > 0) {
        if (value.text().substr(0, 2) !== '{{' || value.text().substr(Math.max(0, value.text().length - 2)) !== '}}') {
            return {value: convert(type, value.text())};
        }
        const defstr = '__default__';
        const converted = convert(type, defstr);
        if (converted === defstr) {
            return {value: converted};
        }
    }
    return {};
}
