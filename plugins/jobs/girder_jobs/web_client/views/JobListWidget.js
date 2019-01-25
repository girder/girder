import $ from 'jquery';
import _ from 'underscore';

import PaginateWidget from '@girder/core/views/widgets/PaginateWidget';
import View from '@girder/core/views/View';
import router from '@girder/core/router';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { defineFlags, formatDate, DATE_SECOND, _whenAll } from '@girder/core/misc';
import eventStream from '@girder/core/utilities/EventStream';
import { getCurrentUser } from '@girder/core/auth';
import { SORT_DESC } from '@girder/core/constants';

import JobCollection from '../collections/JobCollection';
import JobStatus from '../JobStatus';
import JobListWidgetTemplate from '../templates/jobListWidget.pug';
import '../stylesheets/jobListWidget.styl';
import JobListTemplate from '../templates/jobList.pug';

import CheckBoxMenu from './CheckBoxMenu';
import JobGraphWidget from './JobGraphWidget';

var JobListWidget = View.extend({
    events: {
        'click .g-job-trigger-link': function (e) {
            var cid = $(e.currentTarget).attr('cid');
            this.trigger('g:jobClicked', this.collection.get(cid));
        },
        'change select.g-page-size': function (e) {
            this.collection.pageLimit = parseInt($(e.currentTarget).val());
            this.collection.fetch({}, true);
        },
        'change input.g-job-checkbox': function (e) {
            var jobId = $(e.currentTarget).closest('tr').attr('g-job-id');
            if ($(e.currentTarget).is(':checked')) {
                this.jobCheckedStates[jobId] = true;
            } else {
                delete this.jobCheckedStates[jobId];
            }
            this._renderData();
        },
        'click input.g-job-checkbox-all': function (e) {
            e.stopPropagation();
        },
        'change input.g-job-checkbox-all': function (e) {
            if ($(e.currentTarget).is(':checked')) {
                this.collection.forEach((job) => { this.jobCheckedStates[job.id] = true; });
            } else {
                this.jobCheckedStates = {};
            }
            this._renderData();
        },
        'click .check-menu-dropdown a.g-jobs-list-cancel': function (e) {
            this._cancelJobs();
        },
        'click .g-job-worker-task-info': function (event) {
            router.navigate('#plugins/worker/task/status', {trigger: true});
        }
    },

    initialize: function (settings) {
        var currentUser = getCurrentUser();
        this.showAllJobs = !!settings.allJobsMode;
        this.columns = settings.columns || this.columnEnum.COLUMN_ALL;
        this.userId = (settings.filter && !settings.allJobsMode) ? (settings.filter.userId ? settings.filter.userId : currentUser.id) : null;
        this.showGraphs = settings.showGraphs;
        this.showPageSizeSelector = settings.showPageSizeSelector;
        this.showFilters = settings.showFilters;
        this.typeFilter = null;
        this.statusFilter = null;
        this.timingFilter = JobStatus.getAll().reduce((obj, status) => {
            obj[status.text] = true;
            return obj;
        }, {});
        this.jobCheckedStates = {};
        this.jobHighlightStates = {};

        this.jobGraphWidget = null;

        this.pageSizes = [25, 50, 100, 250, 500, 1000];

        this.collection = new JobCollection();
        if (this.showAllJobs) {
            this.collection.resourceName = 'job/all';
        }
        this.collection.sortField = settings.sortField || 'created';
        this.collection.sortDir = settings.sortDir || SORT_DESC;
        this.collection.pageLimit = settings.pageLimit || this.collection.pageLimit;

        this.listenTo(this.collection, 'update reset', this._onDataChange);

        this._fetchWithFilter();

        this.currentView = settings.view ? settings.view : 'list';

        this.showHeader = _.has(settings, 'showHeader') ? settings.showHeader : true;
        this.showPaging = _.has(settings, 'showPaging') ? settings.showPaging : true;
        this.linkToJob = _.has(settings, 'linkToJob') ? settings.linkToJob : true;
        this.triggerJobClick = _.has(settings, 'triggerJobClick') ? settings.triggerJobClick : false;

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.listenTo(eventStream, 'g:event.job_status', this._statusChange);
        this.listenTo(eventStream, 'g:event.job_created', this._jobCreated);
        this.listenTo(eventStream, 'g:eventStream.start', this._fetchWithFilter);

        this.timingFilterWidget = new CheckBoxMenu({
            title: 'Phases',
            items: {},
            parentView: this
        });

        this.typeFilterWidget = new CheckBoxMenu({
            title: 'Type',
            items: {},
            parentView: this
        });

        this.listenTo(this.typeFilterWidget, 'g:triggerCheckBoxMenuChanged', function (e) {
            this.typeFilter = _.keys(e).reduce((arr, key) => {
                if (e[key]) {
                    arr.push(key);
                }
                return arr;
            }, []);
            this._fetchWithFilter();
        });

        this.statusFilterWidget = new CheckBoxMenu({
            title: 'Status',
            items: {},
            parentView: this
        });

        let statusTextToStatusCode = {};
        this.listenTo(this.statusFilterWidget, 'g:triggerCheckBoxMenuChanged', function (e) {
            this.statusFilter = _.keys(e).reduce((arr, key) => {
                if (e[key]) {
                    arr.push(parseInt(statusTextToStatusCode[key]));
                }
                return arr;
            }, []);
            this._fetchWithFilter();
        });

        restRequest({
            url: this.showAllJobs ? 'job/typeandstatus/all' : 'job/typeandstatus',
            method: 'GET'
        }).done((result) => {
            var typesFilter = result.types.reduce((obj, type) => {
                obj[type] = true;
                return obj;
            }, {});
            this.typeFilterWidget.setItems(typesFilter);

            var statusFilter = result.statuses.map((status) => {
                let statusText = JobStatus.text(status);
                statusTextToStatusCode[statusText] = status;
                return statusText;
            }).reduce((obj, statusText) => {
                obj[statusText] = true;
                return obj;
            }, {});
            this.statusFilterWidget.setItems(statusFilter);
        });

        this.render();
    },

    columnEnum: defineFlags([
        'COLUMN_ACTION_CHECKBOX',
        'COLUMN_STATUS_ICON',
        'COLUMN_TITLE',
        'COLUMN_UPDATED',
        'COLUMN_OWNER',
        'COLUMN_TYPE',
        'COLUMN_STATUS'
    ], 'COLUMN_ALL'),

    render: function () {
        this.$el.html(JobListWidgetTemplate({
            currentView: this.currentView,
            pageSize: this.collection.pageLimit,
            pageSizes: this.pageSizes,
            showFilters: this.showFilters,
            showGraphs: this.showGraphs,
            showPageSizeSelector: this.showPageSizeSelector
        }));

        this.typeFilterWidget.setElement(this.$('.g-job-filter-container .type')).render();
        this.statusFilterWidget.setElement(this.$('.g-job-filter-container .status')).render();

        this.$('a[data-toggle="tab"]').on('shown.bs.tab', (e) => {
            this.currentView = $(e.currentTarget).attr('name');
            if (this.userId) {
                router.navigate(`jobs/user/${this.userId}/${this.currentView}`);
            } else {
                router.navigate(`jobs/${this.currentView}`);
            }
            this.render();
        });

        if (this.currentView === 'timing-history' || this.currentView === 'time') {
            if (this.jobGraphWidget) {
                this.jobGraphWidget.remove();
            }
            this.jobGraphWidget = new JobGraphWidget({
                parentView: this,
                el: this.$('.g-main-content'),
                collection: this.collection,
                view: this.currentView,
                timingFilter: this.timingFilter,
                timingFilterWidget: this.timingFilterWidget
            }).render();
        }

        this._renderData();

        return this;
    },

    _onDataChange: function () {
        this.jobCheckedStates = {};
        this._renderData();
    },

    _renderData: function () {
        if (!this.$('.g-main-content').length) {
            // Do nothing until render has been called
            return;
        }

        if (this.collection.isEmpty()) {
            this.$('.g-main-content,.g-job-pagination').hide();
            this.$('.g-no-job-record').show();
            return;
        } else {
            this.$('.g-main-content,.g-job-pagination').show();
            this.$('.g-no-job-record').hide();
        }

        if (this.currentView === 'list') {
            this.$('.g-main-content').html(JobListTemplate({
                jobs: this.collection.toArray(),
                showHeader: this.showHeader,
                columns: this.columns,
                columnEnum: this.columnEnum,
                linkToJob: this.linkToJob,
                triggerJobClick: this.triggerJobClick,
                JobStatus: JobStatus,
                formatDate: formatDate,
                DATE_SECOND: DATE_SECOND,
                jobCheckedStates: this.jobCheckedStates,
                jobHighlightStates: this.jobHighlightStates,
                anyJobChecked: _.find(this.jobCheckedStates, (status) => status === true),
                allJobChecked: this.collection.every((job) => this.jobCheckedStates[job.id])
            }));
        }

        if (this.showPaging) {
            this.paginateWidget.setElement(this.$('.g-job-pagination')).render();
        }
    },

    _statusChange: function (event) {
        let job = this.collection.get(event.data._id);
        if (!job) {
            return;
        }
        job.set(event.data);
        this._renderData();
        this.trySetHighlightRecord(event.data._id);
    },

    _jobCreated: function (event) {
        this._fetchWithFilter()
            .done(() => {
                this.trySetHighlightRecord(event.data._id);
            });
    },

    trySetHighlightRecord: function (jobId) {
        const job = this.collection.get(jobId);
        if (_.isObject(job) && job.id === jobId) {
            this.jobHighlightStates[jobId] = true;
            this._renderData();
            setTimeout(() => {
                delete this.jobHighlightStates[jobId];
                this._renderData();
            }, 1000);
        }
    },

    _fetchWithFilter() {
        var filter = {};
        if (this.userId) {
            filter.userId = this.userId;
        }
        if (this.typeFilter) {
            filter.types = JSON.stringify(this.typeFilter);
        }
        if (this.statusFilter) {
            filter.statuses = JSON.stringify(this.statusFilter);
        }
        this.collection.params = filter;

        return this.collection.fetch({}, true);
    },

    _cancelJobs: function () {
        _whenAll(
            Object.keys(this.jobCheckedStates)
                .filter((jobId) => {
                    var jobModel = this.collection.find((job) => job.id === jobId);
                    return JobStatus.isCancelable(jobModel);
                })
                .map((jobId) => restRequest({
                    url: `job/${jobId}/cancel`,
                    method: 'PUT',
                    error: null
                }))
        ).done((results) => {
            if (!results.length) {
                return;
            }
            events.trigger('g:alert', {
                icon: 'ok',
                text: `Cancel ${results.length === 1 ? 'request' : 'requests'} sent for ${results.length} ${results.length === 1 ? 'job' : 'jobs'}`,
                type: 'info',
                timeout: 4000
            });
        });
    }
});

export default JobListWidget;
