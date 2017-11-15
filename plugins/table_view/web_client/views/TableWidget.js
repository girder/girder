import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';

import datalib from 'datalib';

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
            return datalib.csv;
        }
        if (file.get('mimeType') === 'text/tab-separated-values' || _.contains(['tsv', 'tab'], ext)) {
            return datalib.tsv;
        }
        return null;
    },

    updateData: function () {
        // If we already have the data, just render.
        if (this.data) {
            this.render();
            return;
        }

        const parser = this.tableParser(this.file);
        if (!parser) {
            this.$('.g-item-table-view').remove();
            return this;
        }
        parser(this.file.downloadUrl(), (error, data) => {
            if (error) {
                events.trigger('g:alert', {
                    text: 'An error occurred while attempting to read and ' +
                          'parse the data file. Details have been logged in the console.',
                    type: 'danger',
                    timeout: 5000,
                    icon: 'attention'
                });
                console.error(error);
                return;
            }
            datalib.read(data, {parse: 'auto'});
            this.data = data;
            this.columns = _.keys(data.__types__);
            this.render();
        });
    },

    toggleView: function () {
        this.showData = !this.showData;
        if (this.showData) {
            this.updateData();
        } else {
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
        this.$el.html(TableWidgetTemplate({
            showData: this.showData,
            columns: this.columns,
            rows: this.data,
            page: this.page,
            pageSize: 10
        }));

        return this;
    }
});

export default TableWidget;
