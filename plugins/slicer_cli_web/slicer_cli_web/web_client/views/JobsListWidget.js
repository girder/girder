import OutputParameterDialog from './OutputParameterDialog';

import jobListWidget from '../templates/jobsListWidget.pug';

const $ = girder.$;
const _ = girder._;
const View = girder.views.View;
const { SORT_DESC } = girder.constants;
const eventStream = girder.utilities.eventStream;
const { restRequest, getApiRoot } = girder.rest;

// cache parameter file models
const paramFiles = {};

const JobsListWidget = View.extend({
    events: {
        'click .s-param-file': '_clickParamFile'
    },

    initialize() {
        if (!this.collection) {
            this.collection = new girder.plugins.jobs.collections.JobCollection();

            // We want to display 10 jobs, but we are filtering
            // them on the client, so we fetch extra jobs here.
            // Ideally, we would be able to filter them server side
            // but the /job endpoint doesn't currently have the
            // flexibility to do so.
            this.collection.pageLimit = 50;
            this.collection.sortDir = SORT_DESC;
            this.collection.sortField = 'created';
        }

        this.listenTo(this.collection, 'all', this.render);
        this.listenTo(eventStream, 'g:event.job_status', this.fetchAndRender);
        this.listenTo(eventStream, 'g:event.job_created', this.fetchAndRender);
        this.listenTo(eventStream, 'g:eventStream.start', this.fetchAndRender);
        this.fetchAndRender();
    },

    render() {
        let jobs = this.collection.filter((job, index) => {
            return (job.get('kwargs') || {}).image && (job.get('kwargs') || {}).container_args;
        });
        if (!jobs.length) {
            jobs = this.collection;
        }
        jobs = jobs.slice(0, 10).map((job) => {
            // make an async request to add output parameter information
            // to the job model
            this._paramFile(job);
            return _.extend({paramFile: paramFiles[job.id]}, job.attributes);
        });
        const root = getApiRoot().replace(/\/$/, '').replace(/\/[^/]+$/, '').replace(/\/[^/]+$/, '');

        this.$el.html(jobListWidget({
            jobs,
            JobStatus: girder.plugins.jobs.JobStatus,
            rootLink: root
        }));
        this.$('[data-toggle="tooltip"]').tooltip({container: 'body'});
        return this;
    },

    fetchAndRender() {
        this.collection.fetch(null, true)
            .then(() => this.render());
    },

    _paramFile(job) {
        // we already processed this job
        if (_.has(paramFiles, job.id)) {
            return;
        }

        const bindings = job.get('slicerCLIBindings') || {};
        const outputs = bindings.outputs || {};
        const id = outputs.parameters;

        if (id) {
            // avoid processing this job again
            paramFiles[job.id] = {};

            // check if the file still exists
            restRequest({
                url: `file/${id}`,
                error: null
            }).done((file) => {
                paramFiles[job.id] = file;
                this.render();
            });
        }
    },

    _clickParamFile(evt) {
        const fileId = $(evt.currentTarget).data('file-id');
        restRequest({
            url: `file/${fileId}/download`,
            dataType: 'text'
        }).done((parameters) => {
            const view = new OutputParameterDialog({
                parentView: this,
                el: '#g-dialog-container',
                parameters
            });
            view.render();
        });
    }
});

export default JobsListWidget;
