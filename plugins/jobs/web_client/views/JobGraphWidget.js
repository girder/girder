import _ from 'underscore';
import $ from 'jquery';
import vg from 'vega';
import moment from 'moment';

import View from 'girder/views/View';
import JobStatus from '../JobStatus';
import JobsGraphWidgetTemplate from '../templates/jobsGraphWidget.pug';
import timingHistoryChartConfig from './timingHistoryChartConfig';
import timeChartConfig from './timeChartConfig';

export default View.extend({
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

        this.timingFilterWidget.on('g:triggerCheckBoxMenuChanged', function (e) {
            this.timingFilter = _.extend(this.timingFilter, e);
            this.update();
        }, this);
    },

    render: function () {
        this.$el.empty();
        this.$el.html(JobsGraphWidgetTemplate(this));
        this.timingFilterWidget.setItems(this.timingFilter);
        this.timingFilterWidget.setElement(this.$('.g-job-filter-container .timing')).render();
    },

    remove: function () {
        this.timingFilterWidget.off('g:triggerCheckBoxMenuChanged');
        View.prototype.remove.call(this);
    },

    update: function () {
        var jobs = this.collection.toArray();

        var openDetailView = view => {
            return (event, item) => {
                if (item && (item.itemName === 'bar' || item.itemName === 'circle')) {
                    window.open(`#/job/${item.datum.id}`, '_blank');
                }
            };
        };

        if (this.view === 'timing-history') {
            jobs.forEach(job => job.calculateSegmentation());
            let config = $.extend(true, {}, timingHistoryChartConfig);
            // limit the width to the size of the container. When there are fewer records,
            // further limit the size based on the number of records plus some padding for labels and tooltip to make it looks better
            let width = Math.min(this.$el.width(), jobs.length * 30 + 400);
            // the minimum width needed for each job is 10px
            let numberOfJobs = Math.min(jobs.length, Math.floor(width / 10));
            let vegaData = this._prepareDataForChart(jobs, numberOfJobs);
            let withForEachJob = width / numberOfJobs;
            // if the width for each job is less than 20px, remove axe labels
            if (withForEachJob < 20) {
                config.axes[0].properties.labels.opacity = { value: 0 };
            }
            config.width = width;
            config.height = this.$('.g-jobs-graph').height();
            config.data[0].values = vegaData;
            config.scales[1].type = this.yScale;
            let allStatus = JobStatus.getAll().filter(status => this.timingFilter ? this.timingFilter[status.text] : true);
            config.scales[2].domain = allStatus.map(status => status.text);
            config.scales[2].range = allStatus.map(status => status.color);
            config.scales[3].domain = jobs.map(job => job.get('_id'));
            config.scales[3].range = jobs.map(job => job.get('title'));

            vg.parse.spec(config, chart => {
                var view = chart({
                    el: this.$('.g-jobs-graph').get(0),
                    renderer: 'svg'
                }).update();
                view.on('click', openDetailView(view));
            });

            let positiveTimings = _.clone(this.timingFilter);
            this.timingFilterWidget.setItems(positiveTimings);
        }

        if (this.view === 'time') {
            jobs.forEach(job => job.calculateSegmentation());
            let config = $.extend(true, {}, timeChartConfig);
            // limit the width to the size of the container. When there are fewer records,
            // further limit the size based on the number of records plus some padding for labels and tooltip to make it looks better
            let width = Math.min(this.$el.width(), jobs.length * 30 + 400);
            // the minimum width needed for each job is 6px
            let numberOfJobs = Math.min(jobs.length, Math.floor(width / 6));
            let vegaData = this._prepareDataForChart(jobs, numberOfJobs);
            let withForEachJob = width / numberOfJobs;
            // if the width for each job is less than 20px, remove date axe and axe labels
            if (withForEachJob < 20) {
                config.axes.splice(0, 1);
                config.axes[0].properties.labels.opacity = { value: 0 };
            }
            config.width = width;
            config.height = this.$('.g-jobs-graph').height();
            config.data[0].values = vegaData;
            config.scales[1].type = this.yScale;
            config.scales[2].domain = jobs.map(job => job.get('_id'));
            config.scales[2].range = jobs.map(job => {
                let datetime = moment(job.get('updated')).format('MM/DD');
                return datetime;
            });
            config.scales[3].domain = jobs.map(job => job.get('_id'));
            config.scales[3].range = jobs.map(job => job.get('title'));
            let allStatus = JobStatus.getAll().filter(status => {
                if (status.text !== 'Inactive' && status.text !== 'Queued') {
                    if (this.timingFilter) {
                        return this.timingFilter[status.text];
                    }
                    return false;
                }
                return false;
            });
            config.scales[4].domain = allStatus.map(status => status.text);
            config.scales[4].range = allStatus.map(status => status.color);

            vg.parse.spec(config, chart => {
                var view = chart({
                    el: this.$('.g-jobs-graph').get(0),
                    renderer: 'svg'
                }).update();
                view.on('click', openDetailView(view));
            });

            let positiveTimings = _.clone(this.timingFilter);
            delete positiveTimings['Inactive'];
            delete positiveTimings['Queued'];
            this.timingFilterWidget.setItems(positiveTimings);
        }
    },

    _prepareDataForChart(jobs, numberOfJobs) {
        let allRecords = [];
        jobs.reverse();
        for (var i = 0; i < numberOfJobs; i++) {
            let job = jobs[i];
            let id = job.get('_id');
            let title = job.get('title');
            let currentStatus = JobStatus.text(job.get('status'));
            let updated = moment(job.get('updated')).format('L LT');
            let records = job.get('segments')
                .map(segment => {
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
                .filter(record => this.timingFilter[record.status]);
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
