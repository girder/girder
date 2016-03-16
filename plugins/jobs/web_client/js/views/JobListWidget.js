girder.views.jobs_JobListWidget = girder.View.extend({
    events: {
        'click .g-job-trigger-link': function (e) {
            var cid = $(e.target).attr('cid');
            this.trigger('g:jobClicked', this.collection.get(cid));
        }
    },

    initialize: function (settings) {
        this.columns = settings.columns || this.columnEnum.COLUMN_ALL;
        this.filter = settings.filter || {
            userId: girder.currentUser.id
        };

        this.collection = new girder.collections.JobCollection();
        this.collection.sortField = settings.sortField || 'created';
        this.collection.sortDir = settings.sortDir || girder.SORT_DESC;
        this.collection.pageLimit = settings.pageLimit || this.collection.pageLimit;

        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch(this.filter);

        this.showHeader = _.has(settings, 'showHeader') ? settings.showHeader : true;
        this.showPaging = _.has(settings, 'showPaging') ? settings.showPaging : true;
        this.linkToJob = _.has(settings, 'linkToJob') ? settings.linkToJob : true;
        this.triggerJobClick = _.has(settings, 'triggerJobClick') ? settings.triggerJobClick : false;

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        girder.eventStream.on('g:event.job_status', this._statusChange, this);
    },

    columnEnum: girder.defineFlags([
        'COLUMN_STATUS_ICON',
        'COLUMN_TITLE',
        'COLUMN_UPDATED',
        'COLUMN_OWNER',
        'COLUMN_STATUS'
    ], 'COLUMN_ALL'),

    render: function () {
        this.$el.html(girder.templates.jobs_jobList({
            jobs: this.collection.toArray(),
            showHeader: this.showHeader,
            columns: this.columns,
            columnEnum: this.columnEnum,
            linkToJob: this.linkToJob,
            triggerJobClick: this.triggerJobClick,
            girder: girder
        }));

        if (this.showPaging) {
            this.paginateWidget.setElement(this.$('.g-job-pagination')).render();
        }

        return this;
    },

    _statusChange: function (event) {
        var job = event.data,
            tr = this.$('tr[jobId=' + job._id + ']');

        if (!tr.length) {
            return;
        }

        if (this.columns & this.columnEnum.COLUMN_STATUS_ICON) {
            tr.find('td.g-status-icon-container').attr('status', job.status)
              .find('i').removeClass().addClass(girder.jobs_JobStatus.icon(job.status));
        }
        if (this.columns & this.columnEnum.COLUMN_STATUS) {
            tr.find('td.g-job-status-cell').text(girder.jobs_JobStatus.text(job.status));
        }
        if (this.columns & this.columnEnum.COLUMN_UPDATED) {
            tr.find('td.g-job-updated-cell').text(
                girder.formatDate(job.updated, girder.DATE_SECOND));
        }

        tr.addClass('g-highlight');

        window.setTimeout(function () {
            tr.removeClass('g-highlight');
        }, 1000);
    }
});

girder.router.route('jobs/user/:id', 'jobList', function (id) {
    girder.events.trigger('g:navigateTo', girder.views.jobs_JobListWidget, {
        filter: {userId: id}
    });
});
