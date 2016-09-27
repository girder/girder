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

import '../stylesheets/jobListWidget.styl';

var JobListWidget = View.extend({
    events: {
        'click .g-job-trigger-link': function (e) {
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
    },

    columnEnum: defineFlags([
        'COLUMN_STATUS_ICON',
        'COLUMN_TITLE',
        'COLUMN_UPDATED',
        'COLUMN_OWNER',
        'COLUMN_STATUS'
    ], 'COLUMN_ALL'),

    render: function () {
        this.$el.html(JobListWidgetTemplate({
            jobs: this.collection.toArray(),
            showHeader: this.showHeader,
            columns: this.columns,
            columnEnum: this.columnEnum,
            linkToJob: this.linkToJob,
            triggerJobClick: this.triggerJobClick,
            JobStatus: JobStatus,
            formatDate: formatDate,
            DATE_SECOND: DATE_SECOND
        }));

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
    }
});

export default JobListWidget;
