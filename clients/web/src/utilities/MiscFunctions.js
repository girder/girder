/**
 * This file contains utility functions for general use in the application
 */
girder.DATE_MONTH = 0;
girder.DATE_DAY = 1;
girder.DATE_MINUTE = 2;
girder.DATE_SECOND = 3;

/**
 * Format a date string to the given resolution.
 * @param datestr The date string to format.
 * @param resolution The resolution, defaults to 'day'. Minimum is month.
 */
girder.formatDate = function (datestr, resolution) {
    datestr = datestr.replace(' ', 'T'); // Cross-browser accepted date format
    var date = new Date(datestr);
    var output = girder.MONTHS[date.getMonth()];

    resolution = resolution || girder.DATE_MONTH;

    if (resolution >= girder.DATE_DAY) {
        output += ' ' + date.getDate() + ',';
    }

    output += ' ' + date.getFullYear();

    if (resolution >= girder.DATE_MINUTE) {
        output += ' at ' + date.getHours() + ':' +
            ('0' + date.getMinutes()).slice(-2);
    }
    if (resolution >= girder.DATE_SECOND) {
        output += ':' + ('0' + date.getSeconds()).slice(-2);
    }

    return output;
};

/**
 * Format a size in bytes into a human-readable string with metric unit
 * prefixes.
 */
girder.formatSize = function (sizeBytes) {
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
        ['B', 'kB', 'MB', 'GB', 'TB'][i];
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
girder.confirm = function (params) {
    params = _.extend({
        text: 'Are you sure?',
        yesText: 'Yes',
        yesClass: 'btn-danger',
        noText: 'Cancel',
        escapedHtml: false
    }, params);
    $('#g-dialog-container').html(girder.templates.confirmDialog({
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
girder.localeComparator = function (model1, model2) {
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
girder.localeSort = function (a1, a2) {
    if (a1 !== undefined && a1.localeCompare) {
        return a1.localeCompare(a2);
    }
    return a1 > a2 ? 1 : (a1 < a2 ? -1 : 0);
};

/**
 * Return the model class name given its collection name.
 * @param name Collection name, e.g. 'user'
 */
girder.getModelClassByName = function (name) {
    var className = name.charAt(0).toUpperCase();
    return className + name.substr(1) + 'Model';
};

girder.parseQueryString = function (queryString) {
    var params = {};
    if (queryString) {
        _.each(queryString.replace(/\+/g, ' ').split(/&/g), function (el, i) {
            var aux = el.split('='), o = {}, val;
            if (aux.length > 1) {
                val = decodeURIComponent(el.substr(aux[0].length + 1));
            }
            params[decodeURIComponent(aux[0])] = val;
        });
    }
    return params;
};

girder.cookie = {
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
girder.restartServer = function () {
    function waitForServer() {
        girder.restRequest({
            type: 'GET',
            path: 'system/version',
            error: null
        }).done(_.bind(function (resp) {
            if (resp.serverStartDate !== girder.restartServer._lastStartDate) {
                girder.restartServer._reloadWindow();
            } else {
                window.setTimeout(waitForServer, 1000);
            }
        })).error(_.bind(function () {
            window.setTimeout(waitForServer, 1000);
        }));
    }

    girder.restRequest({
        type: 'GET',
        path: 'system/version'
    }).done(_.bind(function (resp) {
        girder.restartServer._lastStartDate = resp.serverStartDate;
        girder.restartServer._callSystemRestart();
        girder.events.trigger('g:alert', {
            icon: 'cw',
            text: 'Restarting server',
            type: 'warning',
            timeout: 60000
        });
        waitForServer();
    }));
};
/* Having these as object properties facilitates testing */
girder.restartServer._callSystemRestart = function () {
    girder.restRequest({type: 'PUT', path: 'system/restart'});
};
girder.restartServer._reloadWindow = function () {
    window.location.reload();
};

/**
 * Transform markdown into HTML and render it into the given element. If no
 * element is provided, simply returns the HTML.
 *
 * @param val The markdown text input.
 * @param el The element to render the output HTML into, or falsy to simply
 *        return the HTML value.
 */
girder.renderMarkdown = (function () {
    if (window.marked) {
        marked.setOptions({ sanitize: true });
        return function (val, el) {
            if (el) {
                $(el).html(marked(val));
            } else {
                return marked(val);
            }
        };
    } else {
        return function () {
            throw new Error('You must include the marked library to call this function');
        };
    }
}());

(function () {
    var _pluginConfigRoutes = {};

    /**
     * Expose a plugin configuration page via the admin plugins page.
     * @param pluginName The canonical plugin name, i.e. its directory name
     * @param route The route to trigger that will render the plugin config.
     */
    girder.exposePluginConfig = function (pluginName, route) {
        _pluginConfigRoutes[pluginName] = route;
    };

    girder.getPluginConfigRoute = function (pluginName) {
        return _pluginConfigRoutes[pluginName];
    };
}());

/* Pending rest requests are listed in this pool so that they can be aborted or
 * checked if still processing. */
(function () {
    var restXhrPool = {};
    var restXhrCount = 0;
    $(document).ajaxSend(function (event, xhr, opts) {
        restXhrCount += 1;
        xhr.girderXhrNumber = restXhrCount;
        restXhrPool[restXhrCount] = xhr;
    });
    $(document).ajaxComplete(function (event, xhr, opts) {
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
    girder.numberOutstandingRestRequests = function (category) {
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
    girder.cancelRestRequests = function (category) {
        _.each(restXhrPool, function (xhr, num, pool) {
            if (category && (!xhr.girder || !xhr.girder[category])) {
                return;
            }
            if (xhr.abort) {
                xhr.abort();
            }
        });
    };
}());
