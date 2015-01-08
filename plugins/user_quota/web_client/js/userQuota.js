/* Quota and assetstore policy user interface */

(function () {
    _.each({user: 'User', collection: 'Collection'}, function (
            modelName, modelType) {
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
                /* Add the quota menu item to the resource menu as needed */
                girder.views[viewName].__super__.render.call(this);
                var el = $('.g-' + modelType + '-header a.g-delete-' +
                           modelType).closest('li');
                var settings = {girder: girder};
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
                }).on('g:saved', function (resource) {
                    this.render();
                }, this);
            }
        });
        var fullModelName = modelName + 'Model';
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
                    this.set('assetstoreList', new girder.collections.AssetstoreCollection());
                    this.get('assetstoreList').on('g:changed', function () {
                        this.trigger('g:quotaPolicyFetched');
                    }, this).fetch();
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
            e.preventDefault();
            var fields = {
                fileSizeQuota: this.$('#g-fileSizeQuota').val(),
                preferredAssetstore: this.$('#g-preferredAssetstore').val(),
                fallbackAssetstore: this.$('#g-fallbackAssetstore').val()
            };
            var sizeValue = this.$('#g-sizeValue').val();
            var sizeUnits = this.$('#g-sizeUnits').val();
            if (parseFloat(sizeValue) > 0) {
                fields.fileSizeQuota = parseFloat(sizeValue);
                /* parse suffix */
                var suffixes = 'bkMGT';
                var match = sizeValue.match(
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
                for (var i = 0; i < parseInt(sizeUnits); i += 1) {
                    fields.fileSizeQuota *= 1024;
                }
                fields.fileSizeQuota = parseInt(fields.fileSizeQuota);
            } else {
                fields.fileSizeQuota = sizeValue;
            }
            this.updateQuotaPolicies(fields);
            this.$('button.g-save-policies').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.model = settings.model;
        this.modelType = settings.modelType;
        this.model.on('g:quotaPolicyFetched', function () {
            this.render();
        }, this).fetchQuotaPolicy();
    },

    capacityChart: function (view, el) {
        var quota = view.model.get('quotaPolicy').fileSizeQuota;
        if (!quota) {
            $(el).addClass('g-no-chart');
            return;
        }
        $(el).addClass('g-has-chart');
        var used = view.model.get('size');
        var free = used < quota ? quota - used : 0;
        var data = [
            ['Used', used],
            ['Free', free]
        ];
        var plot = $(el).jqplot([data], {
            seriesDefaults: {
                renderer: $.jqplot.PieRenderer,
                rendererOptions: {
                    sliceMargin: 2,
                    shadow: false,
                    highlightMouseOver: false,
                    showDataLabels: true,
                    padding: 5
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
        var quota = this.model.get('quotaPolicy').fileSizeQuota;
        if (!quota) {
            return 'Unlimited';
        }
        var used = this.model.get('size');
        var free = quota - used;
        if (free > 0) {
            return girder.formatSize(free) + ' free of ' +
                girder.formatSize(quota);
        }
        return 'No space left of ' + girder.formatSize(quota);
    },

    render: function () {
        var view = this;
        var name = view.model.attributes.name;
        if (view.modelType === 'user') {
            name = view.model.attributes.firstName + ' ' +
                   view.model.attributes.lastName;
        }
        var sizeUnits = 0;
        var sizeValue = view.model.get('quotaPolicy').fileSizeQuota;
        if (sizeValue) {
            for (sizeUnits = 0; sizeUnits < 4 && parseInt(sizeValue / 1024) *
                    1024 === sizeValue; sizeUnits += 1) {
                sizeValue /= 1024;
            }
        }
        var modal = this.$el.html(girder.templates.quotaPolicies({
            girder: girder,
            model: view.model,
            modelType: view.modelType,
            name: name,
            quotaPolicy: view.model.get('quotaPolicy'),
            sizeValue: sizeValue,
            sizeUnits: sizeUnits,
            assetstoreList: (girder.currentUser.get('admin') ?
                view.model.get('assetstoreList').models : undefined),
            capacityString: ' ' + this.capacityString()
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
