import convert from './convert';

const $ = girder.$;

/**
 * Parse a `contraints` tag.
 */
export default function constraints(type, constraintsTag) {
    const $c = $(constraintsTag);
    const spec = {};
    const min = $c.find('minimum').text();
    const max = $c.find('maximum').text();
    const step = $c.find('step').text();
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
