import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';

import datalib from 'datalib';

import TableWidgetTemplate from '../templates/tableWidget.pug';
import '../stylesheets/tableWidget.styl';

var TableWidget = View.extend({
    events: {
        'click .g-table-view-page-prev:not(.disabled)': 'previousPage',
        'click .g-table-view-page-next:not(.disabled)': 'nextPage'
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;

        this.listenTo(this.item, 'change', function () {
            this.updateData();
        }, this);

        this.page = 0;
        this.data = [];
        this.columns = [];

        this.updateData();
    },

    updateData: function () {
        let parser = null;
        let name = this.item.get('name').toLowerCase();
        if (name.endsWith('.csv')) {
            parser = datalib.csv;
        } else if (name.endsWith('.tsv') || name.endsWith('.tab')) {
            parser = datalib.tsv;
        } else {
            this.$('.g-item-table-view').remove();
            return this;
        }

        parser(this.item.downloadUrl(), (error, data) => {
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
            columns: this.columns,
            rows: this.data,
            page: this.page,
            pageSize: 10
        }));

        return this;
    }
});

export default TableWidget;
