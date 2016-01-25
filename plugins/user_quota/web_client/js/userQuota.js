/* Quota and assetstore policy user interface */

(function () {
    _.each({user: 'User', collection: 'Collection'}, function (
            modelName, modelType) {
        var fullModelName;
        var viewName = modelName + 'View';
        girder.views[viewName] = girder.views[viewName].extend({
            events: function () {
                var eventSelector = 'click .g-' + modelType + '-policies';
                var addedEvents = {};
                addedEvents[eventSelector] = 'editPolicies';
                return $.extend(girder.views[viewName].__super__.events,
                                addedEvents);
            },
            initialize: function (settings) {
                this.quota = ((settings || {}).dialog === 'quota');
                girder.views[viewName].__super__.initialize.apply(this,
                                                                  arguments);
            },
            render: function () {
                var el, settings;
                /* Add the quota menu item to the resource menu as needed */
                girder.views[viewName].__super__.render.call(this);
                el = $('.g-' + modelType + '-header a.g-delete-' +
                       modelType).closest('li');
                settings = {girder: girder};
                settings[modelType] = this.model;
                el.before(girder.templates[modelType + 'PoliciesMenu'](
                    settings));
                if (this.quota) {
                    this.quota = null;
                    this.editPolicies();
                }
            },
            editPolicies: function () {
                new girder.views.QuotaPolicies({
                    el: $('#g-dialog-container'),
                    model: this.model,
                    modelType: modelType,
                    parentView: this
                }).on('g:saved', function () {
                    this.render();
                }, this);
            }
        });
        fullModelName = modelName + 'Model';
        girder.models[fullModelName] = girder.models[fullModelName].extend({
            /* Saves the quota policy on this model to the server.  Saves the
             * state of whatever this model's "quotaPolicy" parameter is set
             * to.  When done, triggers the 'g:quotaPolicySaved' event on the
             * model.
             */
            updateQuotaPolicy: function () {
                girder.restRequest({
                    path: this.resourceName + '/' + this.get('_id') + '/quota',
                    type: 'PUT',
                    error: null,
                    data: {
                        policy: JSON.stringify(this.get('quotaPolicy'))
                    }
                }).done(_.bind(function () {
                    this.trigger('g:quotaPolicySaved');
                }, this)).error(_.bind(function (err) {
                    this.trigger('g:error', err);
                }, this));

                return this;
            },
            /* Fetches the quota policy from the server, and sets it as the
             * quotaPolicy property.
             * @param force: By default, this only fetches quotaPolicy if it
             *               hasn't already been set on the model.  If you want
             *               to force a refresh anyway, set this param to true.
             */
            fetchQuotaPolicy: function (force) {
                this.off('g:fetched').on('g:fetched', function () {
                    this.fetchAssetstores(force);
                });
                if (!this.get('quotaPolicy') || force) {
                    girder.restRequest({
                        path: this.resourceName + '/' + this.get('_id') + '/quota',
                        type: 'GET'
                    }).done(_.bind(function (resp) {
                        this.set('quotaPolicy', resp.quota);
                        this.fetch();
                    }, this)).error(_.bind(function (err) {
                        this.trigger('g:error', err);
                    }, this));
                } else {
                    this.fetch();
                }
                return this;
            },
            /* Fetches the list of assetstores from the server, and sets it as
             * the assetstoreList property.  This is the second part of
             * fetching quota policy, as we need to know the assetstores for
             * the user interface.
             * @param force: By default, this only fetches assetstoreList if it
             *               hasn't already been set on the model.  If you want
             *               to force a refresh anyway, set this param to true.
             */
            fetchAssetstores: function (force) {
                if (girder.currentUser.get('admin') &&
                        (!this.get('assetstoreList') || force)) {
                    this.set('assetstoreList',
                             new girder.collections.AssetstoreCollection());
                    this.get('assetstoreList').on('g:changed', function () {
                        this.fetchDefaultQuota(force);
                    }, this).fetch();
                } else {
                    this.fetchDefaultQuota(force);
                }
                return this;
            },
            /* Fetches the global default setting for quota for this resource.
             * @param force: By default, this only fetches the default quota if
             *               it hasn't already been set on the model.  If you
             *               want to force a refresh anyway, set this param to
             *               true.
             */
            fetchDefaultQuota: function (force) {
                if (girder.currentUser.get('admin') &&
                        (!this.get('defaultQuota') || force)) {
                    girder.restRequest({
                        path: 'system/setting',
                        type: 'GET',
                        data: {
                            key: 'user_quota.default_' + modelType + '_quota'
                        }
                    }).done(_.bind(function (resp) {
                        this.set('defaultQuota', resp);
                        this.trigger('g:quotaPolicyFetched');
                    }, this));
                } else {
                    this.trigger('g:quotaPolicyFetched');
                }
                return this;
            }
        });
    });
    girder.views.UploadWidget = girder.views.UploadWidget.extend({
        uploadNextFile: function () {
            this.$('.g-drop-zone').addClass('hide');
            girder.views.UploadWidget.__super__.uploadNextFile.call(this);
            this.currentFile.on('g:upload.error', function (info) {
                if (info.identifier === 'user_quota.upload-exceeds-quota') {
                    this.$('.g-drop-zone').removeClass('hide');
                }
            }, this).on('g:upload.errorStarting', function (info) {
                if (info.identifier === 'user_quota.upload-exceeds-quota') {
                    this.$('.g-drop-zone').removeClass('hide');
                }
            }, this);
        }
    });
}());

girder.views.QuotaPolicies = girder.View.extend({
    events: {
        'submit #g-policies-edit-form': function (e) {
            var fields;
            e.preventDefault();
            fields = {
                fileSizeQuota: this.$('#g-fileSizeQuota').val(),
                useQuotaDefault: $('input:radio[name=defaultQuota]:checked')
                    .val() === 'True',
                preferredAssetstore: this.$('#g-preferredAssetstore').val(),
                fallbackAssetstore: this.$('#g-fallbackAssetstore').val()
            };
            fields.fileSizeQuota = girder.userQuota.valueAndUnitsToSize(
                this.$('#g-sizeValue').val(), this.$('#g-sizeUnits').val());
            this.updateQuotaPolicies(fields);
            this.$('button.g-save-policies').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },
        'input #g-sizeValue': '_selectCustomQuota',
        'change #g-sizeUnits': '_selectCustomQuota'
    },

    initialize: function (settings) {
        this.model = settings.model;
        this.modelType = settings.modelType;
        this.model.off('g:quotaPolicyFetched').on('g:quotaPolicyFetched',
            function () {
                this.render();
            }, this).fetchQuotaPolicy();
    },

    _selectCustomQuota: function () {
        $('#g-customQuota').prop('checked', true);
    },

    capacityChart: function (view, el) {
        var used, free, data;
        var quota = view.model.get('quotaPolicy').fileSizeQuota;
        if (view.model.get('quotaPolicy').useQuotaDefault !== false) {
            quota = view.model.get('defaultQuota');
            if (!quota) {
                quota = this.model.get('quotaPolicy')._currentFileSizeQuota;
            }
        }
        if (!quota) {
            $(el).addClass('g-no-chart');
            return;
        }
        $(el).addClass('g-has-chart');
        used = view.model.get('size');
        free = Math.max(quota - used, 0);
        data = [
            ['Used (' + girder.formatSize(used) + ')', used],
            ['Free (' + girder.formatSize(free) + ')', free]
        ];
        $(el).jqplot([data], {
            seriesDefaults: {
                renderer: $.jqplot.PieRenderer,
                rendererOptions: {
                    sliceMargin: 2,
                    shadow: false,
                    highlightMouseOver: false,
                    showDataLabels: true,
                    padding: 5,
                    startAngle: 180
                }
            },
            legend: {
                show: true,
                location: 'e',
                background: 'transparent',
                border: 'none'
            },
            grid: {
                background: 'transparent',
                border: 'none',
                borderWidth: 0,
                shadow: false
            },
            gridPadding: {top: 10, right: 10, bottom: 10, left: 10}
        });
    },

    capacityString: function () {
        var used, free;
        var quota = this.model.get('quotaPolicy').fileSizeQuota;
        if (this.model.get('quotaPolicy').useQuotaDefault !== false) {
            quota = this.model.get('defaultQuota');
            if (!quota) {
                quota = this.model.get('quotaPolicy')._currentFileSizeQuota;
            }
        }
        if (!quota) {
            return 'Unlimited';
        }
        used = this.model.get('size');
        free = quota - used;
        if (free > 0) {
            return girder.formatSize(free) + ' free of ' +
                girder.formatSize(quota);
        }
        return 'No space left of ' + girder.formatSize(quota);
    },

    render: function () {
        var view = this;
        var sizeInfo, defaultQuota, defaultQuotaString, modal;
        var name = view.model.attributes.name;
        if (view.modelType === 'user') {
            name = view.model.attributes.firstName + ' ' +
                   view.model.attributes.lastName;
        }
        sizeInfo = girder.userQuota.sizeToValueAndUnits(
            view.model.get('quotaPolicy').fileSizeQuota);
        defaultQuota = this.model.get('defaultQuota');
        if (!defaultQuota) {
            defaultQuotaString = 'Unlimited';
        } else {
            defaultQuotaString = girder.formatSize(defaultQuota);
        }
        modal = this.$el.html(girder.templates.quotaPolicies({
            girder: girder,
            model: view.model,
            modelType: view.modelType,
            name: name,
            quotaPolicy: view.model.get('quotaPolicy'),
            sizeValue: sizeInfo.sizeValue,
            sizeUnits: sizeInfo.sizeUnits,
            assetstoreList: (girder.currentUser.get('admin')
                ? view.model.get('assetstoreList').models : undefined),
            capacityString: ' ' + this.capacityString(),
            defaultQuotaString: defaultQuotaString
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-fileSizeQuota').focus();
            view.capacityChart(view, '.g-quota-capacity-chart');
        }).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('quota');
        });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));
        view.$('#g-fileSizeQuota').focus();
        girder.dialogs.handleOpen('quota');
        return this;
    },

    updateQuotaPolicies: function (fields) {
        var view = this;
        _.each(fields, function (value, key) {
            view.model.get('quotaPolicy')[key] = value;
        });
        this.model.on('g:quotaPolicySaved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).off('g:error').on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-policies').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).updateQuotaPolicy();
    }
});

girder.userQuota = {
    /* Convert a number of bytes to a value and units.  The units are the
     * powers of 1024.  For instance, 4096 will result in (4, 1).
     * @param sizeValue: number of bytes to convert.  If this is falsy, an
     *                   empty string is returned.
     * @return .sizeValue: the new size value.  This may be an empty string.
     * @return .sizeUnits: the size units (0-based powers of 1024). */
    sizeToValueAndUnits: function (sizeValue) {
        var sizeUnits = 0;
        if (sizeValue) {
            for (sizeUnits = 0; sizeUnits < 4 && parseInt(sizeValue / 1024, 10) *
                    1024 === sizeValue; sizeUnits += 1) {
                sizeValue /= 1024;
            }
        } else {
            sizeValue = '';
        }
        return {sizeUnits: sizeUnits, sizeValue: sizeValue};
    },

    /* Convert a number and units to a number of bytes.  The units can either
     * be included as a suffix for the number or are the power of 1024.
     * @param sizeValue: an integer, empty string, or a string with a floating
     *                   point number followed by an SI prefix.
     * @param sizeUnits: the size units (0-based powers of 1024).  Ignored if
     *                   units are given in the string.
     * @return sizeBytes: the number of bytes specified, or the empty string
     *                    for none. */
    valueAndUnitsToSize: function (sizeValue, sizeUnits) {
        var sizeBytes = sizeValue;
        var match, i, suffixes = 'bkMGT';
        if (parseFloat(sizeValue) > 0) {
            sizeBytes = parseFloat(sizeValue);
            /* parse suffix */
            match = sizeValue.match(
                new RegExp('^\\s*[0-9.]+\\s*([' + suffixes + '])', 'i'));
            if (match && match.length > 1) {
                for (sizeUnits = 0; sizeUnits < suffixes.length;
                     sizeUnits += 1) {
                    if (match[1].toLowerCase() ===
                            suffixes[sizeUnits].toLowerCase()) {
                        break;
                    }
                }
            }
            for (i = 0; i < parseInt(sizeUnits, 10); i += 1) {
                sizeBytes *= 1024;
            }
            sizeBytes = parseInt(sizeBytes, 10);
        }
        return sizeBytes;
    }
};
