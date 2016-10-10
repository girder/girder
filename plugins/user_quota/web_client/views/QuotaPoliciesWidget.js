import _ from 'underscore';

import View from 'girder/views/View';
import { formatSize } from 'girder/misc';
import { getCurrentUser } from 'girder/auth';
import { handleOpen, handleClose } from 'girder/dialog';
import { valueAndUnitsToSize, sizeToValueAndUnits } from '../utilities/Conversions';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

import QuotaPoliciesWidgetTemplate from '../templates/quotaPoliciesWidget.pug';

var QuotaPoliciesWidget = View.extend({
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
            fields.fileSizeQuota = valueAndUnitsToSize(
                this.$('#g-sizeValue').val(), this.$('#g-sizeUnits').val());
            this.updateQuotaPolicies(fields);
            this.$('button.g-save-policies').girderEnable(false);
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
            ['Used (' + formatSize(used) + ')', used],
            ['Free (' + formatSize(free) + ')', free]
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
            return formatSize(free) + ' free of ' +
                formatSize(quota);
        }
        return 'No space left of ' + formatSize(quota);
    },

    render: function () {
        var view = this;
        var sizeInfo, defaultQuota, defaultQuotaString, modal;
        var name = view.model.attributes.name;
        var currentUser = getCurrentUser();
        if (view.modelType === 'user') {
            name = view.model.attributes.firstName + ' ' +
                   view.model.attributes.lastName;
        }
        sizeInfo = sizeToValueAndUnits(
            view.model.get('quotaPolicy').fileSizeQuota);
        defaultQuota = this.model.get('defaultQuota');
        if (!defaultQuota) {
            defaultQuotaString = 'Unlimited';
        } else {
            defaultQuotaString = formatSize(defaultQuota);
        }
        modal = this.$el.html(QuotaPoliciesWidgetTemplate({
            currentUser: currentUser,
            model: view.model,
            modelType: view.modelType,
            name: name,
            quotaPolicy: view.model.get('quotaPolicy'),
            sizeValue: sizeInfo.sizeValue,
            sizeUnits: sizeInfo.sizeUnits,
            assetstoreList: (currentUser.get('admin')
                ? view.model.get('assetstoreList').models : undefined),
            capacityString: ' ' + this.capacityString(),
            defaultQuotaString: defaultQuotaString
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-fileSizeQuota').focus();
            view.capacityChart(view, '.g-quota-capacity-chart');
        }).on('hidden.bs.modal', function () {
            handleClose('quota');
        });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));
        view.$('#g-fileSizeQuota').focus();
        handleOpen('quota');
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
            this.$('button.g-save-policies').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).updateQuotaPolicy();
    }
});

export default QuotaPoliciesWidget;
