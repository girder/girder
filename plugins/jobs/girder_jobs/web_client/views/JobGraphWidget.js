import _ from 'underscore';
import $ from 'jquery';
import { parse,
    View as VegaView } from 'vega-lib/build/vega';
import moment from 'moment';

import View from '@girder/core/views/View';

import JobStatus from '../JobStatus';
import JobsGraphWidgetTemplate from '../templates/jobsGraphWidget.pug';

import timingHistoryChartConfig from './timingHistoryChartConfig';
import timeChartConfig from './timeChartConfig';

const JobGraphWidget = View.extend({
    events: {
        'change input.linear-scale': function (e) {
            this.yScale = $(e.target).is(':checked') ? 'linear' : 'sqrt';
            this.update();
        }
    },

    initialize: function (settings) {
        this.view = settings.view;
        this.collection = settings.collection;
        this.timingFilterWidget = settings.timingFilterWidget;
        this.timingFilter = settings.timingFilter;

        this.yScale = 'sqrt';

        this.listenTo(this.timingFilterWidget, 'g:triggerCheckBoxMenuChanged', function (e) {
            this.timingFilter = _.extend(this.timingFilter, e);
            this.update();
        });
        this.listenTo(this.collection, 'update reset', this.update);
    },

    render: function () {
        this.$el.html(JobsGraphWidgetTemplate(this));
        this.timingFilterWidget.setItems(this.timingFilter);
        this.timingFilterWidget.setElement(this.$('.g-job-filter-container .timing')).render();
        this.update();
        return this;
    },

    remove: function () {
        this.timingFilterWidget.off('g:triggerCheckBoxMenuChanged');
        View.prototype.remove.call(this);
    },

    update: function () {
        var openDetailView = (view) => {
            return (event, item) => {
                if (item && (item.itemName === 'bar' || item.itemName === 'circle')) {
                    window.open(`#/job/${item.datum.id}`, '_blank');
                }
            };
        };

        if (this.view === 'timing-history') {
            let config = $.extend(true, {}, timingHistoryChartConfig);
            // limit the width to the size of the container. When there are fewer records,
            // further limit the size based on the number of records plus some padding for labels and tooltip to make it looks better
            let width = Math.min(this.$el.width(), this.collection.size() * 30 + 400);
            // the minimum width needed for each job is 10px
            let numberOfJobs = Math.min(this.collection.size(), Math.floor(width / 10));
            let vegaData = this._prepareDataForChart(numberOfJobs);
            let widthForEachJob = width / numberOfJobs;
            // if the width for each job is less than 20px, remove axe labels
            if (widthForEachJob < 20) {
                config.axes[0].encode.labels.opacity = { value: 0 };
            }
            config.width = width;
            config.height = this.$('.g-jobs-graph').height();
            config.data[0].values = vegaData;

            const minval = Math.min(0, Math.min.apply(this, vegaData.map((d) => d.elapsed === undefined ? 10 : d.elapsed)) / 1000);
            config.data[1].values = [minval < -86400 ? -86400 : minval];

            config.scales[1].type = this.yScale;
            let allStatus = JobStatus.getAll().filter((status) => this.timingFilter ? this.timingFilter[status.text] : true);
            config.scales[2].domain = allStatus.map((status) => status.text);
            config.scales[2].range = allStatus.map((status) => status.color);
            config.scales[3].domain = this.collection.pluck('_id');
            config.scales[3].range = this.collection.pluck('title');

            const runtime = parse(config);
            const view = new VegaView(runtime)
                .initialize(this.$('.g-jobs-graph')[0])
                .renderer('svg')
                .hover()
                .run();
            view.addEventListener('click', openDetailView(view));

            let positiveTimings = _.clone(this.timingFilter);
            this.timingFilterWidget.setItems(positiveTimings);
        }

        if (this.view === 'time') {
            let config = $.extend(true, {}, timeChartConfig);
            // limit the width to the size of the container. When there are fewer records,
            // further limit the size based on the number of records plus some padding for labels and tooltip to make it looks better
            let width = Math.min(this.$el.width(), this.collection.size() * 30 + 400);
            // the minimum width needed for each job is 6px
            let numberOfJobs = Math.min(this.collection.size(), Math.floor(width / 6));
            let vegaData = this._prepareDataForChart(numberOfJobs);
            let widthForEachJob = width / numberOfJobs;
            // if the width for each job is less than 20px, remove date axe and axe labels
            if (widthForEachJob < 20) {
                config.axes.splice(0, 1);
                config.axes[0].encode.labels.opacity = { value: 0 };
            }
            config.width = width;
            config.height = this.$('.g-jobs-graph').height();
            config.data[0].values = vegaData;
            config.scales[1].type = this.yScale;
            config.scales[2].domain = this.collection.pluck('_id');
            config.scales[2].range = this.collection.map(
                (job) => moment(job.get('updated')).format('MM/DD'));
            config.scales[3].domain = this.collection.pluck('_id');
            config.scales[3].range = this.collection.pluck('title');
            let allStatus = JobStatus.getAll().filter((status) => {
                if (status.text !== 'Inactive' && status.text !== 'Queued') {
                    if (this.timingFilter) {
                        return this.timingFilter[status.text];
                    }
                    return false;
                }
                return false;
            });
            config.scales[4].domain = allStatus.map((status) => status.text);
            config.scales[4].range = allStatus.map((status) => status.color);

            const runtime = parse(config);
            const view = new VegaView(runtime)
                .initialize(this.$('.g-jobs-graph')[0])
                .renderer('svg')
                .hover()
                .run();
            view.addEventListener('click', openDetailView(view));

            let positiveTimings = _.clone(this.timingFilter);
            delete positiveTimings['Inactive'];
            delete positiveTimings['Queued'];
            this.timingFilterWidget.setItems(positiveTimings);
        }
    },

    _prepareDataForChart(numberOfJobs) {
        let allRecords = [];

        for (var i = numberOfJobs - 1; i >= 0; i--) {
            let job = this.collection.at(i);
            let id = job.get('_id');
            let title = job.get('title');
            let currentStatus = JobStatus.text(job.get('status'));
            let updated = moment(job.get('updated')).format('L LT');
            let records = job.calculateSegmentation()
                .map((segment) => {
                    let status = segment.status;
                    let elapsed = '';
                    switch (status) {
                        case 'Inactive':
                            elapsed = -segment.elapsed;
                            break;
                        case 'Queued':
                            elapsed = -segment.elapsed;
                            break;
                        default:
                            elapsed = segment.elapsed;
                    }
                    return {
                        id: id,
                        title: title,
                        updated: updated,
                        status: status,
                        currentStatus: currentStatus,
                        elapsed: elapsed
                    };
                })
                .filter((record) => this.timingFilter[record.status]);
            if (records.length) {
                allRecords = records.concat(allRecords);
            } else {
                allRecords.unshift({
                    id: id,
                    title: title,
                    updated: updated,
                    currentStatus: currentStatus
                });
            }
        }
        return allRecords;
    }
});

export default JobGraphWidget;
