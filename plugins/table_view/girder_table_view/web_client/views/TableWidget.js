import _ from 'underscore';

import View from 'girder/views/View';

import * as loader from 'vega-loader';

import TableWidgetTemplate from '../templates/tableWidget.pug';
import '../stylesheets/tableWidget.styl';

var TableWidget = View.extend({
    events: {
        'click .g-item-table-view-header': 'toggleView',
        'click .g-table-view-page-prev:not(.disabled)': 'previousPage',
        'click .g-table-view-page-next:not(.disabled)': 'nextPage'
    },

    initialize: function (settings) {
        this.file = settings.files.at(0);
        this.showData = false;
        this.page = 0;
        this.data = null;
        this.columns = null;
        this.states = {
            VIEW_COLLAPSED: 0,
            DATA_TOO_LARGE: 1,
            DATA_LOADING: 2,
            DATA_ERROR: 3,
            DATA_READY: 4
        };
        const MAX_FILE_SIZE = 30e6; // 30MB
        this.state = this.states.VIEW_COLLAPSED;
        if (this.file.get('size') > MAX_FILE_SIZE) {
            this.state = this.states.DATA_TOO_LARGE;
        }
        if (this.tableParser(this.file)) {
            this.render();
        }
    },

    tableParser: function (file) {
        if (!file) {
            return null;
        }
        const ext = file.get('exts')[file.get('exts').length - 1];
        if (file.get('mimeType') === 'text/csv' || ext === 'csv') {
            return 'csv';
        }
        if (file.get('mimeType') === 'text/tab-separated-values' || _.contains(['tsv', 'tab'], ext)) {
            return 'tsv';
        }
        return null;
    },

    updateData: function () {
        // If we already have the data, just render.
        if (this.data) {
            this.state = this.states.DATA_READY;
            this.render();
            return;
        }

        const parser = this.tableParser(this.file);
        if (!parser) {
            this.$('.g-item-table-view').remove();
            return this;
        }
        loader.loader().load(this.file.downloadUrl()).then((data) => {
            data = loader.read(data, {type: parser, parse: 'auto'});
            this.data = data;
            this.columns = _.keys(data[0]);
            this.state = this.states.DATA_READY;
            this.render();
            return data;
        }, (error) => {
            console.error(error);
            this.state = this.states.DATA_ERROR;
            this.render();
            return null;
        });
    },

    toggleView: function () {
        if (this.state === this.states.VIEW_COLLAPSED) {
            this.state = this.states.DATA_LOADING;
            this.render();
            this.updateData();
        } else if (this.state === this.states.DATA_READY) {
            this.state = this.states.VIEW_COLLAPSED;
            this.render();
        }
    },

    previousPage: function () {
        this.page -= 1;
        this.render();
    },

    nextPage: function () {
        this.page += 1;
        this.render();
    },

    render: function () {
        let message = '';
        if (this.state === this.states.DATA_ERROR) {
            message = 'An error occurred while attempting to read and parse the data file';
        } else if (this.state === this.states.DATA_TOO_LARGE) {
            message = 'Data is too large to preview';
        } else if (this.state === this.states.DATA_LOADING) {
            message = 'Loading...';
        }
        this.$el.html(TableWidgetTemplate({
            state: this.state,
            states: this.states,
            message: message,
            fileName: this.file.get('name'),
            columns: this.columns,
            rows: this.data,
            page: this.page,
            pageSize: 10
        }));

        return this;
    }
});

export default TableWidget;
