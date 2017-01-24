import _ from 'underscore';

import panel from './panel';

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

    gui.panels = _.map($spec.find('executable > parameters'), panel);
    return gui;
}

export default parse;
