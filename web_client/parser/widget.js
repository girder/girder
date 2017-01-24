/**
 * Mapping from slicer parameter specs to control widget types.
 * @param {XML} param The full xml parameter spec
 * @return {string} The widget type
 */
function widget(param) {
    var typeMap = {
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
        image: 'image',
        file: 'file',
        directory: 'directory'
    };
    return typeMap[param.tagName];
}

export default widget;
