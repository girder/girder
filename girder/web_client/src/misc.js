import $ from 'jquery';
import _ from 'underscore';
import Remarkable from 'remarkable';

import { MONTHS } from '@girder/core/constants';

/**
 * This file contains utility functions for general use in the application
 */
var DATE_MONTH = 0;
var DATE_DAY = 1;
var DATE_MINUTE = 2;
var DATE_SECOND = 3;

/**
 * Format a date string to the given resolution.
 * @param datestr The date string to format.
 * @param resolution The resolution, defaults to 'day'. Minimum is month.
 */
function formatDate(datestr, resolution) {
    datestr = datestr.replace(' ', 'T'); // Cross-browser accepted date format
    var date = new Date(datestr);
    var output = MONTHS[date.getMonth()];

    resolution = resolution || DATE_MONTH;

    if (resolution >= DATE_DAY) {
        output += ' ' + date.getDate() + ',';
    }

    output += ' ' + date.getFullYear();

    if (resolution >= DATE_MINUTE) {
        output += ' at ' + date.getHours() + ':' +
            ('0' + date.getMinutes()).slice(-2);
    }
    if (resolution >= DATE_SECOND) {
        output += ':' + ('0' + date.getSeconds()).slice(-2);
    }

    return output;
}

/**
 * Format a size in bytes into a human-readable string with metric unit
 * prefixes.
 */
function formatSize(sizeBytes) {
    if (sizeBytes < 1024) {
        return sizeBytes + ' B';
    }
    var i, sizeVal = sizeBytes, precision = 1;
    for (i = 0; sizeVal >= 1024; i += 1) {
        sizeVal /= 1024;
    }
    // If we are just reporting a low number, no need for decimal places.
    if (sizeVal < 10) {
        precision = 3;
    } else if (sizeVal < 100) {
        precision = 2;
    }
    return sizeVal.toFixed(precision) + ' ' +
        ['B', 'kB', 'MB', 'GB', 'TB'][Math.min(i, 4)];
}

/**
 * Like formatSize, but more generic. Returns a human-readable format
 * of an integer using metric prefixes. The caller is expected to append any
 * unit string if necessary.
 *
 * @param {integer} n The number to format.
 * @param {Object} [opts={}] Formatting options. These include:
 *   - {integer} [maxLen] Max number of digits in the output.
 *   - {integer} [base=1000] Base for the prefixes (usually 1000 or 1024).
 *   - {string} [sep=''] Separator between numeric value and metric prefix.
 */
function formatCount(n, opts) {
    n = n || 0;
    opts = opts || {};

    var i = 0,
        base = opts.base || 1000,
        sep = opts.sep || '',
        maxLen = opts.maxLen || 3,
        precision = maxLen - 1;

    for (; n > base; i += 1) {
        n /= base;
    }

    if (!i) {
        precision = 0;
    } else if (n > 100) {
        precision -= 2;
    } else if (n > 10) {
        precision -= 1;
    }

    return n.toFixed(Math.max(0, precision)) + sep +
        ['', 'k', 'M', 'G', 'T'][Math.min(i, 4)];
}

/**
 * This comparator can be used by collections that wish to support locale-based
 * sorting.  The locale specifies how upper and lower case are compared.
 */
function localeComparator(model1, model2) {
    var a1 = model1.get(this.sortField),
        a2 = model2.get(this.sortField);

    if (a1 !== undefined && a1.localeCompare) {
        var result = a1.localeCompare(a2) * this.sortDir;
        if (result || !this.secondarySortField) {
            return result;
        }
        a1 = model1.get(this.secondarySortField);
        a2 = model2.get(this.secondarySortField);
        return a1.localeCompare(a2) * this.sortDir;
    }

    return a1 > a2 ? this.sortDir : (a1 < a2 ? -this.sortDir : 0);
}

/**
 * This comparator can be passed to the sort function on javascript arrays.
 */
function localeSort(a1, a2) {
    if (a1 !== undefined && a1.localeCompare) {
        return a1.localeCompare(a2);
    }
    return a1 > a2 ? 1 : (a1 < a2 ? -1 : 0);
}

/**
 * Return the model class name given its collection name.
 * @param name Collection name, e.g. 'user'
 */
function getModelClassByName(name) {
    var className = name.charAt(0).toUpperCase();
    return className + name.substr(1) + 'Model';
}

function parseQueryString(queryString) {
    var params = {};
    if (queryString) {
        _.each(queryString.replace(/\+/g, ' ').split(/&/g), function (el) {
            var aux = el.split('='), val;
            if (aux.length > 1) {
                val = decodeURIComponent(el.substr(aux[0].length + 1));
            }
            params[decodeURIComponent(aux[0])] = val;
        });
    }
    return params;
}

/**
 * Create a set of flags that can be OR'd (|) together to define a set of
 * options.
 *
 * @param {Array} options An array of strings defining the option names.
 * @param {string} allOption If you want an option that enables all options,
 *                 pass its name as this parameter.
 * @return {Object} An object mapping the names of options to values.
 */
function defineFlags(options, allOption) {
    var i = 0,
        obj = {};

    if (allOption) {
        obj[allOption] = 1;
    }
    _.each(options, function (opt) {
        obj[opt] = 1 << i;

        if (allOption) {
            obj[allOption] |= obj[opt];
        }

        i += 1;
    });

    return obj;
}

/**
 * Transform markdown into HTML and render it into the given element. If no
 * element is provided, simply returns the HTML.
 *
 * @param val The markdown text input.
 * @param el The element to render the output HTML into, or falsy to simply
 *        return the HTML value.
 */
var renderMarkdown = (function () {
    var md = new Remarkable({
        linkify: true
    });
    return function (val, el) {
        if (el) {
            $(el).html(md.render(val));
        } else {
            return md.render(val);
        }
    };
}());

/**
 * Capitalize the first character of a string.
 */
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.substring(1);
}

function splitRoute(route) {
    if (!route) {
        return { base: '', name: '' };
    }
    var firstIndex = route.indexOf('?'),
        lastIndex = route.lastIndexOf('?'),
        dialogName,
        baseRoute;

    if (firstIndex === -1) {
        baseRoute = route;
    } else {
        baseRoute = route.slice(0, firstIndex);
    }

    if (lastIndex === -1) {
        dialogName = '';
    } else {
        dialogName = route.slice(lastIndex + 1);
    }

    return { name: dialogName, base: baseRoute };
}

function _whenAll(promises) {
    return $.when(...promises).then((...results) => results);
}

export {
    DATE_MONTH,
    DATE_DAY,
    DATE_MINUTE,
    DATE_SECOND,
    formatDate,
    formatSize,
    formatCount,
    localeComparator,
    localeSort,
    getModelClassByName,
    parseQueryString,
    defineFlags,
    renderMarkdown,
    capitalize,
    splitRoute,
    _whenAll
};
