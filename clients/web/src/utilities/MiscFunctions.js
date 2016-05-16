var _         = require('underscore');
var Rest      = require('girder/rest');
var Constants = require('girder/constants');
var Events    = require('girder/events');

var ConfirmDialogTemplate = require('girder/templates/widgets/confirmDialog.jade');

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
var formatDate = function (datestr, resolution) {
    datestr = datestr.replace(' ', 'T'); // Cross-browser accepted date format
    var date = new Date(datestr);
    var output = Constants.MONTHS[date.getMonth()];

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
var formatSize = function (sizeBytes) {
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
var formatCount = function (n, opts) {
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
var confirm = function (params) {
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
var localeComparator = function (model1, model2) {
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
var localeSort = function (a1, a2) {
    if (a1 !== undefined && a1.localeCompare) {
        return a1.localeCompare(a2);
    }
    return a1 > a2 ? 1 : (a1 < a2 ? -1 : 0);
};

/**
 * Return the model class name given its collection name.
 * @param name Collection name, e.g. 'user'
 */
var getModelClassByName = function (name) {
    var className = name.charAt(0).toUpperCase();
    return className + name.substr(1) + 'Model';
};

var parseQueryString = function (queryString) {
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

var cookie = {
    findAll: function () {
        var cookies = {};
        _(document.cookie.split(';'))
            .chain()
            .map(function (m) {
                return m.replace(/^\s+/, '').replace(/\s+$/, '');
            })
            .each(function (c) {
                var arr = c.split('='),
                    key = arr[0],
                    value = null,
                    size = _.size(arr);
                if (size > 1) {
                    value = arr.slice(1).join('');
                }
                cookies[key] = value;
            });
        return cookies;
    },

    find: function (name) {
        var cookie = null,
            list = this.findAll();

        _.each(list, function (value, key) {
            if (key === name) {
                cookie = value;
            }
        });
        return cookie;
    }
};

/**
 * Restart the server, wait until it has restarted, then reload the current
 * page.
 */
var restartServer = function () {
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
var defineFlags = function (options, allOption) {
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
var renderMarkdown = (function () {
    if (window.Remarkable) {
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
    } else {
        return function () {
            throw new Error(
                'You must include the remarkable library to call this function');
        };
    }
}());

/**
 * Capitalize the first character of a string.
 */
var capitalize = function (str) {
    return str.charAt(0).toUpperCase() + str.substring(1);
};

var _pluginConfigRoutes = {};

/**
 * Expose a plugin configuration page via the admin plugins page.
 * @param pluginName The canonical plugin name, i.e. its directory name
 * @param route The route to trigger that will render the plugin config.
 */
var exposePluginConfig = function (pluginName, route) {
    _pluginConfigRoutes[pluginName] = route;
};

var getPluginConfigRoute = function (pluginName) {
    return _pluginConfigRoutes[pluginName];
};

/* Pending rest requests are listed in this pool so that they can be aborted or
* checked if still processing. */
var restXhrPool = {};
var restXhrCount = 0;
$(document).ajaxSend(function (event, xhr) {
    restXhrCount += 1;
    xhr.girderXhrNumber = restXhrCount;
    restXhrPool[restXhrCount] = xhr;
});
$(document).ajaxComplete(function (event, xhr) {
    var num = xhr.girderXhrNumber;
    if (num && restXhrPool[num]) {
        delete restXhrPool[num];
    }
});
/* Get the number of outstanding rest requests.
 * :param category: if specified, only count those requests that have
 *                  xhr.girder.(category) set to a truthy value.
 * :returns: the number of outstanding requests.
 */
var numberOutstandingRestRequests = function (category) {
    if (category) {
        return _.filter(restXhrPool, function (xhr) {
            return xhr.girder && xhr.girder[category];
        }).length;
    }
    return _.size(restXhrPool);
};
/* Cancel outstanding rest requests.
 * :param category: if specified, only abort those requests that have
 *                  xhr.girder.(category) set to a truthy value.
 */
var cancelRestRequests = function (category) {
    _.each(restXhrPool, function (xhr) {
        if (category && (!xhr.girder || !xhr.girder[category])) {
            return;
        }
        if (xhr.abort) {
            xhr.abort();
        }
    });
};

module.exports = {
    DATE_MONTH: DATE_MONTH,
    DATE_DAY: DATE_DAY,
    DATE_MINUTE: DATE_MINUTE,
    DATE_SECOND: DATE_SECOND,
    formatDate: formatDate,
    formatSize: formatSize,
    formatCount: formatCount,
    confirm: confirm,
    localeComparator: localeComparator,
    localeSort: localeSort,
    getModelClassByName: getModelClassByName,
    parseQueryString: parseQueryString,
    cookie: cookie,
    restartServer: restartServer,
    defineFlags: defineFlags,
    renderMarkdown: renderMarkdown,
    capitalize: capitalize,
    exposePluginConfig: exposePluginConfig,
    getPluginConfigRoute: getPluginConfigRoute,
    numberOutstandingRestRequests: numberOutstandingRestRequests,
    cancelRestRequests: cancelRestRequests
};

