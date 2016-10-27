import _ from 'underscore';

/**
 * This is a parser for Slicer's GUI Schema:
 *   https://www.slicer.org/slicerWiki/index.php/Slicer3:Execution_Model_Documentation#XML_Schema
 */

/**
 * Parse a Slicer GUI spec into a json object for rendering
 * the controlsPanel view.  This function parses into the following structure:
 *
 * * global metadata
 *   * panels[] -- each is rendered in a different panel
 *     * groups[] -- each is rendered together seperated by a horizontal line
 *       * parameters[] -- individual parameters
 *
 * @param {string|object} spec The slicer GUI spec content (accepts parsed or unparsed xml)
 * @returns {object}
 */
function parse(spec) {
    var gui, $spec;

    if (_.isString(spec)) {
        spec = $.parseXML(spec);
    }

    $spec = $(spec).find('executable:first');

    // top level metadata
    gui = {
        title: $spec.find('executable > title').text(),
        description: $spec.find('executable > description').text()
    };

    // optional metadata
    _.each(
        ['version', 'documentation-url', 'license', 'contributor', 'acknowledgements'],
        function (key) {
            var val = $spec.find('executable > ' + key + ':first');
            if (val.length) {
                gui[key] = val.text();
            }
        }
    );

    gui.panels = _.map($spec.find('executable > parameters'), _parsePanel);
    return gui;
}

/**
 * Parse a <parameters> tag into a "panel" object.
 */
function _parsePanel(panel) {
    var $panel = $(panel);
    return {
        advanced: $panel.attr('advanced') === 'true',
        groups: _.map($panel.find('parameters > label'), _parseGroup)
    };
}

/**
 * Parse a parameter group (deliminated by <label> tags) within a
 * panel.
 */
function _parseGroup(label) {
    // parameter groups inside panels
    var $label = $(label),
        $description = $label.next('description');

    return {
        label: $label.text(),
        description: $description.text(),
        parameters: _.map($description.nextUntil('label'), _parseParam)
    };
}

/**
 * Parse a parameter spec.
 * @param {XML} param The parameter spec
 * @returns {object}
 */
function _parseParam(param) {
    var $param = $(param);
    var type = _widgetType(param);
    var values = {};
    var channel = $param.find('channel');

    if (channel.length) {
        channel = channel.text();
    } else {
        channel = 'input';
    }

    if ((type === 'file' || type === 'image') && channel === 'output') {
        type = 'new-file';
    }

    if (!type) {
        console.warn('Unhandled parameter type "' + param.tagName + '"'); // eslint-disable-line no-console
    }

    if (type === 'string-enumeration' || type === 'number-enumeration') {
        values = {
            values: _.map($param.find('element'), (el) => {
                return convertValue(type, $(el).text());
            })
        };
    }

    return _.extend(
        {
            type: type,
            slicerType: param.tagName,
            id: $param.find('name').text() || $param.find('longflag').text(),
            title: $param.find('label').text(),
            description: $param.find('description').text(),
            channel: channel
        },
        values,
        _parseDefault(type, $param.find('default')),
        _parseConstraints(type, $param.find('constraints').get(0))
    );
}

/**
 * Mapping from slicer parameter specs to control widget types.
 * @param {XML} param The full xml parameter spec
 * @return {string} The widget type
 */
function _widgetType(param) {
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

/**
 * Convert from a string to the given value type.
 * @param {string} type A widget type
 * @param {string} value The value to be converted
 * @returns {*} The converted value
 */
function convertValue(type, value) {
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

/**
 * Parse a `default` tag returning an empty object when no default is given.
 */
function _parseDefault(type, value) {
    var output = {};
    if (value.length) {
        output = {value: convertValue(type, value.text())};
    }
    return output;
}

/**
 * Parse a `contraints` tag.
 */
function _parseConstraints(type, constraints) {
    var $c = $(constraints);
    var spec = {};
    var min = $c.find('minimum').text();
    var max = $c.find('maximum').text();
    var step = $c.find('step').text();
    if (min) {
        spec.min = convertValue(type, min);
    }
    if (max) {
        spec.max = convertValue(type, max);
    }
    if (step) {
        spec.step = convertValue(type, step);
    }
    return spec;
}

export default parse;
