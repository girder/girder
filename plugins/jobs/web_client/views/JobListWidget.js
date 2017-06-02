import $ from 'jquery';
import _ from 'underscore';

import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import View from 'girder/views/View';
import router from 'girder/router';
import events from 'girder/events';
import { restRequest } from 'girder/rest';
import { defineFlags, formatDate, DATE_SECOND } from 'girder/misc';
import eventStream from 'girder/utilities/EventStream';
import { getCurrentUser } from 'girder/auth';
import { SORT_DESC } from 'girder/constants';

import JobCollection from '../collections/JobCollection';
import JobListWidgetTemplate from '../templates/jobListWidget.pug';
import JobListTemplate from '../templates/jobList.pug';
import JobStatus from '../JobStatus';
import CheckBoxMenu from './CheckBoxMenu';
import JobGraphWidget from './JobGraphWidget';

import '../stylesheets/jobListWidget.styl';

var JobListWidget = View.extend({
    events: {
        'click .g-job-trigger-link': function (e) {
            var cid = $(e.target).attr('cid');
            this.trigger('g:jobClicked', this.collection.get(cid));
        },
        'change select.g-page-size': function (e) {
            this.collection.pageLimit = parseInt($(e.target).val());
            this.collection.fetch({}, true);
        },
        'change input.g-job-checkbox': function (e) {
            var jobId = $(e.target).closest('tr').attr('g-job-id');
            if ($(e.target).is(':checked')) {
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
            if ($(e.target).is(':checked')) {
                this.jobs.forEach(job => { this.jobCheckedStates[job.id] = true; });
            } else {
                this.jobCheckedStates = {};
            }
            this._renderData();
        },
        'click .check-menu-dropdown a.g-jobs-list-cancel': function (e) {
            this._cancelJobs();
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
        Object.defineProperty(this, 'jobs', {
            get: () => this.collection.toArray()
        });
        Object.defineProperty(this, 'anyJobChecked', {
            get: () => Object.keys(this.jobCheckedStates).find(key => this.jobCheckedStates[key])
        });
        Object.defineProperty(this, 'allJobChecked', {
            get: () => !this.jobs.find(job => !this.jobCheckedStates[job.id])
        });

        this.jobGraphWidget = null;

        this.pageSizes = [25, 50, 100, 250, 500, 1000];

        this.collection = new JobCollection();
        if (this.showAllJobs) {
            this.collection.resourceName = 'job/all';
        }
        this.collection.sortField = settings.sortField || 'created';
        this.collection.sortDir = settings.sortDir || SORT_DESC;
        this.collection.pageLimit = settings.pageLimit || this.collection.pageLimit;

        this.collection
            .on('g:changed', this._onDataChange, this)
            .on('add', this._onDataChange, this);

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

        eventStream.on('g:event.job_status', this._statusChange, this);
        eventStream.on('g:event.job_created', this._jobCreated, this);

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

        this.typeFilterWidget.on('g:triggerCheckBoxMenuChanged', function (e) {
            this.typeFilter = _.keys(e).reduce((arr, key) => {
                if (e[key]) {
                    arr.push(key);
                }
                return arr;
            }, []);
            this._fetchWithFilter();
        }, this);

        this.statusFilterWidget = new CheckBoxMenu({
            title: 'Status',
            items: {},
            parentView: this
        });

        let statusTextToStatusCode = {};
        this.statusFilterWidget.on('g:triggerCheckBoxMenuChanged', function (e) {
            this.statusFilter = _.keys(e).reduce((arr, key) => {
                if (e[key]) {
                    arr.push(parseInt(statusTextToStatusCode[key]));
                }
                return arr;
            }, []);
            this._fetchWithFilter();
        }, this);

        restRequest({
            path: this.showAllJobs ? 'job/typeandstatus/all' : 'job/typeandstatus',
            method: 'GET'
        }).done(result => {
            var typesFilter = result.types.reduce((obj, type) => {
                obj[type] = true;
                return obj;
            }, {});
            this.typeFilterWidget.setItems(typesFilter);

            var statusFilter = result.statuses.map(status => {
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
        this.$el.html(JobListWidgetTemplate($.extend({}, this, {
            pageSize: this.collection.pageLimit
        })));

        this.typeFilterWidget.setElement(this.$('.g-job-filter-container .type')).render();
        this.statusFilterWidget.setElement(this.$('.g-job-filter-container .status')).render();

        this.$('a[data-toggle="tab"]').on('shown.bs.tab', e => {
            this.currentView = $(e.target).attr('name');
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
            });
            this.jobGraphWidget.render();
        }

        this._renderData();

        return this;
    },

    _onDataChange: function () {
        this.jobCheckedStates = {};
        this._renderData();
    },

    _renderData: function () {
        if (!this.jobs.length) {
            this.$('.g-main-content,.g-job-pagination').hide();
            this.$('.g-no-job-record').show();
            return;
        } else {
            this.$('.g-main-content,.g-job-pagination').show();
            this.$('.g-no-job-record').hide();
        }

        if (this.currentView === 'list') {
            this.$('.g-main-content').html(JobListTemplate({
                jobs: this.jobs,
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
                allJobChecked: this.allJobChecked,
                anyJobChecked: this.anyJobChecked
            }));
        }

        if (this.currentView === 'timing-history' || this.currentView === 'time') {
            this.jobGraphWidget.update(this.jobs);
        }

        if (this.showPaging) {
            this.paginateWidget.setElement(this.$('.g-job-pagination')).render();
        }
    },

    _statusChange: function (event) {
        let job = _.find(this.jobs, job => job.get('_id') === event.data._id);
        if (!job) {
            return;
        }
        job.set(event.data);
        this._renderData();
        this.trySetHighlightRecord(event.data._id);
    },

    _jobCreated: function (event) {
        this._fetchWithFilter()
            .then(() => {
                this.trySetHighlightRecord(event.data._id);
            });
    },

    trySetHighlightRecord: function (jobId) {
        if (this.jobs.find(job => job.id === jobId)) {
            this.jobHighlightStates[jobId] = true;
            this._renderData();
            setTimeout(() => {
                delete this.jobHighlightStates[jobId];
                this._renderData();
            }, 1000);
        }
    },

    _fetchWithFilter() {
        return new Promise((resolve, reject) => {
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
            this.collection.fetch({}, true);
            var callback = () => {
                this.collection.off('g:changed', callback);
                resolve();
            };
            this.collection.on('g:changed', callback);
        });
    },

    _cancelJobs: function () {
        Promise.all(
            Object.keys(this.jobCheckedStates)
                .filter(jobId => {
                    var status = this.jobs.find(job => job.id === jobId).get('status');
                    return [JobStatus.CANCELED, JobStatus.SUCCESS, JobStatus.ERROR].indexOf(status) === -1;
                })
                .map(jobId => Promise.resolve(restRequest({
                    path: `job/${jobId}/cancel`,
                    type: 'PUT',
                    error: null
                })))
        ).then(results => {
            if (!results.length) {
                return;
            }
            events.trigger('g:alert', {
                icon: 'ok',
                text: `Cancel requests sent for ${results.length} ${results.length === 1 ? 'job' : 'jobs'}`,
                type: 'info',
                timeout: 4000
            });
        });
    }
});

export default JobListWidget;
