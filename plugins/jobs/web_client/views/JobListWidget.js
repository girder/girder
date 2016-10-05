import _ from 'underscore';

import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import View from 'girder/views/View';
import { defineFlags, formatDate, DATE_SECOND } from 'girder/misc';
import eventStream from 'girder/utilities/EventStream';
import { getCurrentUser } from 'girder/auth';
import { SORT_DESC } from 'girder/constants';

import JobCollection from '../collections/JobCollection';
import JobListWidgetTemplate from '../templates/jobListWidget.pug';
import JobStatus from '../JobStatus';
import CheckBoxMenu from './CheckBoxMenu';

import '../stylesheets/jobListWidget.styl';

var JobListWidget = View.extend({
    events: {
        'click .g-job-checkbox-menu input': function (e) {
            var cid = $(e.target).attr('cid');
            this.trigger('g:jobClicked', this.collection.get(cid));
        }
    },

    initialize: function (settings) {
        var currentUser = getCurrentUser();
        this.columns = settings.columns || this.columnEnum.COLUMN_ALL;
        this.filter = settings.filter || {
            userId: currentUser.id
        };
        this.typeFilter = {};
        this.statusFilter = {};

        this.collection = new JobCollection();
        this.collection.sortField = settings.sortField || 'created';
        this.collection.sortDir = settings.sortDir || SORT_DESC;
        this.collection.pageLimit = settings.pageLimit || this.collection.pageLimit;

        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch(this.filter);

        this.showHeader = _.has(settings, 'showHeader') ? settings.showHeader : true;
        this.showPaging = _.has(settings, 'showPaging') ? settings.showPaging : true;
        this.linkToJob = _.has(settings, 'linkToJob') ? settings.linkToJob : true;
        this.triggerJobClick = _.has(settings, 'triggerJobClick') ? settings.triggerJobClick : false;

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        eventStream.on('g:event.job_status', this._statusChange, this);

        this.filterTypeMenuWidget = new CheckBoxMenu({
            title: 'Type',
            values: [],
            parentView: this
        });

        this.filterTypeMenuWidget.on('g:triggerCheckBoxMenuChanged', function (e) {
            this.typeFilter = _.clone(e);
            this.render();
        }, this);

        this.filterStatusMenuWidget = new CheckBoxMenu({
            title: 'Status',
            values: [],
            parentView: this
        });

        this.filterStatusMenuWidget.on('g:triggerCheckBoxMenuChanged', function (e) {
            this.statusFilter = _.clone(e);
            this.render();
        }, this);
    },

    columnEnum: defineFlags([
        'COLUMN_STATUS_ICON',
        'COLUMN_TITLE',
        'COLUMN_UPDATED',
        'COLUMN_OWNER',
        'COLUMN_TYPE',
        'COLUMN_STATUS'
    ], 'COLUMN_ALL'),

    render: function () {
        var jobs = this._filterJobs(this.collection.toArray()), types, states;

        this.$el.html(JobListWidgetTemplate({
            jobs: jobs,
            showHeader: this.showHeader,
            columns: this.columns,
            columnEnum: this.columnEnum,
            linkToJob: this.linkToJob,
            triggerJobClick: this.triggerJobClick,
            JobStatus: JobStatus,
            formatDate: formatDate,
            DATE_SECOND: DATE_SECOND
        }));

        types = _.uniq(this.collection.toArray().map(function (job) {
            return job.attributes.type ? job.attributes.type : '';
        }));

        this._updateFilter(this.typeFilter, types);
        this.filterTypeMenuWidget.setValues(this.typeFilter);

        states = _.uniq(this.collection.toArray().map(function (job) {
            return JobStatus.text(job.attributes.status);
        }));
        this._updateFilter(this.statusFilter, states);
        this.filterStatusMenuWidget.setValues(this.statusFilter);

        this.filterTypeMenuWidget.setElement(this.$('.g-job-type-header')).render();
        this.filterStatusMenuWidget.setElement(this.$('.g-job-status-header')).render();

        if (this.showPaging) {
            this.paginateWidget.setElement(this.$('.g-job-pagination')).render();
        }

        return this;
    },

    _statusChange: function (event) {
        var job = event.data,
            tr = this.$('tr[g-job-id=' + job._id + ']');

        if (!tr.length) {
            return;
        }

        if (this.columns & this.columnEnum.COLUMN_STATUS_ICON) {
            tr.find('td.g-status-icon-container').attr('status', job.status)
              .find('i').removeClass().addClass(JobStatus.icon(job.status));
        }
        if (this.columns & this.columnEnum.COLUMN_STATUS) {
            tr.find('td.g-job-status-cell').text(JobStatus.text(job.status));
        }
        if (this.columns & this.columnEnum.COLUMN_UPDATED) {
            tr.find('td.g-job-updated-cell').text(
                formatDate(job.updated, DATE_SECOND));
        }

        tr.addClass('g-highlight');

        window.setTimeout(function () {
            tr.removeClass('g-highlight');
        }, 1000);
    },
    _filterJobs: function (jobs) {
        var filterJobs = [];
        // Include all jobs that match the type and status filters. Jobs that
        // have an undefined type are mapped to '', this is added as a filter
        // option for the user to select.
        filterJobs = this.collection.filter(_.bind(function (job) {
            return ((_.isEmpty(this.typeFilter) ||
                        this.typeFilter[job.attributes.type ? job.attributes.type : '']) &&
                    (_.isEmpty(this.statusFilter) ||
                        this.statusFilter[JobStatus.text(job.attributes.status)]));
        }, this));

        return filterJobs;
    },
    _updateFilter: function (filter, newValues) {
        // We need to work out what keys have been removed or added
        // so we can update the filter. We do this rather than created
        // a new filter inorder to preserve the existing user selections.
        var currentValues = _.keys(filter), added, removed;
        added = _.difference(newValues, currentValues);
        removed = _.difference(currentValues, newValues);

        _.each(added, function (value) {
            filter[value] = true;
        });
        _.each(removed, function (value) {
            delete filter[value];
        });
    }
});

export default JobListWidget;
