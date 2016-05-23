import $                     from 'jquery';
import _                     from 'underscore';
import Remarkable            from 'remarkable';

import ConfirmDialogTemplate from 'girder/templates/widgets/confirmDialog.jade';
import { MONTHS }            from 'girder/constants';
import Events                from 'girder/events';
import Rest                  from 'girder/rest';

import 'bootstrap/js/modal';
import 'girder/utilities/jQuery'; // $.girderModal

/**
 * This file contains utility functions for general use in the application
 */
export var DATE_MONTH = 0;
export var DATE_DAY = 1;
export var DATE_MINUTE = 2;
export var DATE_SECOND = 3;

/**
 * Format a date string to the given resolution.
 * @param datestr The date string to format.
 * @param resolution The resolution, defaults to 'day'. Minimum is month.
 */
export var formatDate = function (datestr, resolution) {
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
};

/**
 * Format a size in bytes into a human-readable string with metric unit
 * prefixes.
 */
export var formatSize = function (sizeBytes) {
    if (sizeBytes < 20000) {
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
};

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
export var formatCount = function (n, opts) {
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
};

/**
 * Prompt the user to confirm an action.
 * @param [text] The text to prompt the user with.
 * @param [yesText] The text for the confirm button.
 * @param [yesClass] Class string to apply to the confirm button.
 * @param [noText] The text for the no/cancel button.
 * @param [escapedHtml] If you want to render the text as HTML rather than
 *        plain text, set this to true to acknowledge that you have escaped any
 *        user-created data within the text to prevent XSS exploits.
 * @param confirmCallback Callback function when the user confirms the action.
 */
export var confirm = function (params) {
    params = _.extend({
        text: 'Are you sure?',
        yesText: 'Yes',
        yesClass: 'btn-danger',
        noText: 'Cancel',
        escapedHtml: false
    }, params);
    $('#g-dialog-container').html(ConfirmDialogTemplate({
        params: params
    })).girderModal(false);

    var el = $('#g-dialog-container').find('.modal-body>p');
    if (params.escapedHtml) {
        el.html(params.text);
    } else {
        el.text(params.text);
    }

    $('#g-confirm-button').unbind('click').click(function () {
        $('#g-dialog-container').modal('hide');
        params.confirmCallback();
    });
};

/**
 * This comparator can be used by collections that wish to support locale-based
 * sorting.  The locale specifies how upper and lower case are compared.
 */
export var localeComparator = function (model1, model2) {
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
};

/**
 * This comparator can be passed to the sort function on javascript arrays.
 */
export var localeSort = function (a1, a2) {
    if (a1 !== undefined && a1.localeCompare) {
        return a1.localeCompare(a2);
    }
    return a1 > a2 ? 1 : (a1 < a2 ? -1 : 0);
};

/**
 * Return the model class name given its collection name.
 * @param name Collection name, e.g. 'user'
 */
export var getModelClassByName = function (name) {
    var className = name.charAt(0).toUpperCase();
    return className + name.substr(1) + 'Model';
};

export var parseQueryString = function (queryString) {
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
};

/**
 * Restart the server, wait until it has restarted, then reload the current
 * page.
 */
export var restartServer = function () {
    function waitForServer() {
        Rest.restRequest({
            type: 'GET',
            path: 'system/version',
            error: null
        }).done(_.bind(function (resp) {
            if (resp.serverStartDate !== restartServer._lastStartDate) {
                restartServer._reloadWindow();
            } else {
                window.setTimeout(waitForServer, 1000);
            }
        })).error(_.bind(function () {
            window.setTimeout(waitForServer, 1000);
        }));
    }

    Rest.restRequest({
        type: 'GET',
        path: 'system/version'
    }).done(_.bind(function (resp) {
        restartServer._lastStartDate = resp.serverStartDate;
        restartServer._callSystemRestart();
        Events.trigger('g:alert', {
            icon: 'cw',
            text: 'Restarting server',
            type: 'warning',
            timeout: 60000
        });
        waitForServer();
    }));
};
/* Having these as object properties facilitates testing */
restartServer._callSystemRestart = function () {
    Rest.restRequest({type: 'PUT', path: 'system/restart'});
};
restartServer._reloadWindow = function () {
    window.location.reload();
};

/**
 * Create a set of flags that can be OR'd (|) together to define a set of
 * options.
 *
 * @param {Array} options An array of strings defining the option names.
 * @param {string} allOption If you want an option that enables all options,
 *                 pass its name as this parameter.
 * @return {Object} An object mapping the names of options to values.
 */
export var defineFlags = function (options, allOption) {
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
};

/**
 * Transform markdown into HTML and render it into the given element. If no
 * element is provided, simply returns the HTML.
 *
 * @param val The markdown text input.
 * @param el The element to render the output HTML into, or falsy to simply
 *        return the HTML value.
 */
export var renderMarkdown = (function () {
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
export var capitalize = function (str) {
    return str.charAt(0).toUpperCase() + str.substring(1);
};

var _pluginConfigRoutes = {};

/**
 * Expose a plugin configuration page via the admin plugins page.
 * @param pluginName The canonical plugin name, i.e. its directory name
 * @param route The route to trigger that will render the plugin config.
 */
export var exposePluginConfig = function (pluginName, route) {
    _pluginConfigRoutes[pluginName] = route;
};

export var getPluginConfigRoute = function (pluginName) {
    return _pluginConfigRoutes[pluginName];
};
