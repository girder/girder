import param from './param';

const $ = girder.$;
const _ = girder._;

/**
 * Parse a parameter group (deliminated by <label> tags) within a
 * panel.
 */
export default function group(label, opts = {}) {
    // parameter groups inside panels
    const $label = $(label);
    const $description = $label.siblings('description').length === 1 ? $label.siblings('description') : $label.next('description');
    const paramlist = ($label.siblings('label').length ? $label.nextUntil('label') : $label.siblings()).filter(':not(description)');
    const parameters = _.filter(
        _.map(paramlist, (p) => param(p, opts)),
        _.isObject
    );

    // don't add the panel if there are no input parameters
    if (parameters.length === 0) {
        return null;
    }

    return {
        label: $label.text(),
        description: $description.text(),
        parameters
    };
}
