import _ from 'underscore';

import group from './group';

/**
 * Parse a <parameters> tag into a "panel" object.
 */
function panel(panelTag) {
    var $panel = $(panelTag);
    return {
        advanced: $panel.attr('advanced') === 'true',
        groups: _.map($panel.find('parameters > label'), group)
    };
}

export default panel;
