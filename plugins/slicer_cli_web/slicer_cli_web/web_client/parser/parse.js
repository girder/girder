import panel from './panel';

const $ = girder.$;
const _ = girder._;

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
 *     * groups[] -- each is rendered together separated by a horizontal line
 *       * parameters[] -- individual parameters
 *
 * @param {string|object} spec The slicer GUI spec content (accepts parsed or unparsed xml)
 * @param {object} [opts] When provided this object will used to provide information about
 *     the outputs of the spec.
 * @returns {object}
 */
export default function parse(spec, opts = {}) {
    if (_.isString(spec)) {
        spec = $.parseXML(spec);
    }

    const $spec = $(spec).find('executable:first');

    // top level metadata
    const gui = {
        title: $spec.find('executable > title').text(),
        description: $spec.find('executable > description').text()
    };

    // optional metadata
    ['version', 'documentation-url', 'license', 'contributor', 'acknowledgements'].forEach((key) => {
        const val = $spec.find(`executable > ${key}:first`);
        if (val.length > 0) {
            gui[key] = val.text();
        }
    });

    gui.panels = _.filter(
        _.map($spec.find('executable > parameters'), (p) => panel(p, opts)),
        _.isObject
    );

    return gui;
}
