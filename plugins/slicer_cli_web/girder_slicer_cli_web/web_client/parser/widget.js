/**
 * Mapping from slicer parameter specs to control widget types.
 * @param {XML} param The full xml parameter spec
 * @return {string} The widget type
 */
export default function widget(param) {
    const typeMap = {
        integer: 'number',
        float: 'number',
        double: 'number',
        boolean: 'boolean',
        string: 'string',
        'integer-vector': 'number-vector',
        'float-vector': 'number-vector',
        'double-vector': 'number-vector',
        'string-vector': 'string-vector',
        'integer-enumeration': 'number-enumeration',
        'float-enumeration': 'number-enumeration',
        'double-enumeration': 'number-enumeration',
        'string-enumeration': 'string-enumeration',
        region: 'region',
        image: 'image',
        file: 'file',
        item: 'item',
        directory: 'directory',
        multi: 'multi'
    };
    return typeMap[param.tagName];
}
