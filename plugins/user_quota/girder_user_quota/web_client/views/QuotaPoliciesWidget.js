import $ from 'jquery';
import _ from 'underscore';

import View from '@girder/core/views/View';
import { formatSize } from '@girder/core/misc';
import { getCurrentUser } from '@girder/core/auth';
import { handleOpen, handleClose } from '@girder/core/dialog';
import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

import { valueAndUnitsToSize, sizeToValueAndUnits } from '../utilities/Conversions';
import QuotaPoliciesWidgetTemplate from '../templates/quotaPoliciesWidget.pug';

const QuotaPoliciesWidget = View.extend({
    events: {
        'submit #g-policies-edit-form': function (e) {
            e.preventDefault();
            const fields = {
                fileSizeQuota: this.$('#g-fileSizeQuota').val(),
                useQuotaDefault: $('input:radio[name=defaultQuota]:checked')
                    .val() === 'True',
                preferredAssetstore: this.$('#g-preferredAssetstore').val(),
                fallbackAssetstore: this.$('#g-fallbackAssetstore').val()
            };
            fields.fileSizeQuota = valueAndUnitsToSize(
                this.$('#g-user-quota-size-value').val(),
                this.$('#g-user-quota-size-units').val());
            this.updateQuotaPolicies(fields);
            this.$('button.g-save-policies').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        },
        'input #g-user-quota-size-value': '_selectCustomQuota',
        'change #g-user-quota-size-units': '_selectCustomQuota'
    },

    initialize: function (settings) {
        this.model = settings.model;
        this.modelType = settings.modelType;
        this.plots = [];
        this.model.off('g:quotaPolicyFetched').on('g:quotaPolicyFetched',
            function () {
                this.render();
            }, this).fetchQuotaPolicy();
    },

    destroy: function () {
        this._destroyPlots();
        View.prototype.destroy.call(this);
    },

    _destroyPlots: function () {
        for (const plot of this.plots) {
            plot.data('jqplot').destroy();
        }
        this.plots = [];
    },

    _selectCustomQuota: function () {
        $('#g-customQuota').prop('checked', true);
    },

    capacityChart: function (view, el) {
        let quota = view.model.get('quotaPolicy').fileSizeQuota;
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
        const used = view.model.get('size');
        const free = Math.max(quota - used, 0);
        const data = [
            ['Used (' + formatSize(used) + ')', used],
            ['Free (' + formatSize(free) + ')', free]
        ];
        const plot = $(el).jqplot([data], {
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
            gridPadding: { top: 10, right: 10, bottom: 10, left: 10 }
        });
        this.plots.push(plot);
    },

    capacityString: function () {
        let quota = this.model.get('quotaPolicy').fileSizeQuota;
        if (this.model.get('quotaPolicy').useQuotaDefault !== false) {
            quota = this.model.get('defaultQuota');
            if (!quota) {
                quota = this.model.get('quotaPolicy')._currentFileSizeQuota;
            }
        }
        if (!quota && quota !== 0) {
            return 'Unlimited';
        }
        const used = this.model.get('size');
        const free = quota - used;
        if (free > 0) {
            return formatSize(free) + ' free of ' +
                formatSize(quota);
        }
        return 'No space left of ' + formatSize(quota);
    },

    render: function () {
        const name = this.model.name();
        const currentUser = getCurrentUser();
        const sizeInfo = sizeToValueAndUnits(
            this.model.get('quotaPolicy').fileSizeQuota);
        const defaultQuota = this.model.get('defaultQuota');
        let defaultQuotaString;
        if (!defaultQuota && defaultQuota !== 0) {
            defaultQuotaString = 'Unlimited';
        } else {
            defaultQuotaString = formatSize(defaultQuota);
        }
        this._destroyPlots();
        const modal = this.$el.html(QuotaPoliciesWidgetTemplate({
            currentUser: currentUser,
            model: this.model,
            modelType: this.modelType,
            name: name,
            quotaPolicy: this.model.get('quotaPolicy'),
            sizeValue: sizeInfo.sizeValue,
            sizeUnits: sizeInfo.sizeUnits,
            assetstoreList: currentUser.get('admin') ? this.model.get('assetstoreList').models : undefined,
            capacityString: ' ' + this.capacityString(),
            defaultQuotaString: defaultQuotaString
        })).girderModal(this).on('shown.bs.modal', () => {
            this.$('#g-fileSizeQuota').trigger('focus');
            this.capacityChart(this, '.g-quota-capacity-chart');
        }).on('hidden.bs.modal', () => {
            handleClose('quota');
            this.trigger('g:hidden');
        });
        modal.trigger($.Event('ready.girder.modal', { relatedTarget: modal }));
        this.$('#g-fileSizeQuota').trigger('focus');
        handleOpen('quota');
        return this;
    },

    updateQuotaPolicies: function (fields) {
        _.each(fields, (value, key) => {
            this.model.get('quotaPolicy')[key] = value;
        });
        this.model.on('g:quotaPolicySaved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).off('g:error').on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-policies').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).trigger('focus');
        }, this).updateQuotaPolicy();
    }
});

export default QuotaPoliciesWidget;
