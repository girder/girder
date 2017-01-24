import _ from 'underscore';

import param from './param';

/**
 * Parse a parameter group (deliminated by <label> tags) within a
 * panel.
 */
function group(label) {
    // parameter groups inside panels
    var $label = $(label),
        $description = $label.next('description');

    return {
        label: $label.text(),
        description: $description.text(),
        parameters: _.map($description.nextUntil('label'), param)
    };
}

export default group;
