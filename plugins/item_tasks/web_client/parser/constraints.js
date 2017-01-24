import convert from './convert';

/**
 * Parse a `contraints` tag.
 */
function constraints(type, constraintsTag) {
    var $c = $(constraintsTag);
    var spec = {};
    var min = $c.find('minimum').text();
    var max = $c.find('maximum').text();
    var step = $c.find('step').text();
    if (min) {
        spec.min = convert(type, min);
    }
    if (max) {
        spec.max = convert(type, max);
    }
    if (step) {
        spec.step = convert(type, step);
    }
    return spec;
}

export default constraints;
