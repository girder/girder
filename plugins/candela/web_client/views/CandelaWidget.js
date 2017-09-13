import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';
import candela from 'candela';
import 'candela/plugins/vega/load';
import 'candela/plugins/treeheatmap/load';

import datalib from 'girder_plugins/candela/node/datalib';

import CandelaWidgetTemplate from '../templates/candelaWidget.pug';
import '../stylesheets/candelaWidget.styl';

import CandelaParametersView from './CandelaParametersView';

var CandelaWidget = View.extend({
    events: {
        'change .g-item-candela-component': 'updateComponent'
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this._components = _.keys(_.pick(candela.components, (comp) => comp.options));

        this.listenTo(this.item, 'change', function () {
            this.render();
        }, this);

        this.parametersView = new CandelaParametersView({
            component: candela.components[this.$('.g-item-candela-component').val()],
            parentView: this
        });

        this.render();
    },

    updateComponent: function () {
        this.parametersView.setComponent(candela.components[this.$('.g-item-candela-component').val()]);
    },

    render: function () {
        let parser = null;
        let name = this.item.get('name').toLowerCase();
        if (name.endsWith('.csv')) {
            parser = datalib.csv;
        } else if (name.endsWith('.tsv') || name.endsWith('.tab')) {
            parser = datalib.tsv;
        } else {
            this.$('.g-item-candela').remove();
            return this;
        }

        this.$el.html(CandelaWidgetTemplate({
            components: this._components
        }));
        this.parametersView.setElement(this.$('.g-item-candela-parameters'));
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

            // Vega has issues with empty-string fields and fields with dots, so rename those.
            let rename = [];
            _.each(data.__types__, (value, key) => {
                if (key === '') {
                    rename.push({from: '', to: 'id'});
                } else if (key.indexOf('.') >= 0) {
                    rename.push({from: key, to: key.replace(/\./g, '_')});
                }
            });

            _.each(rename, (d) => {
                data.__types__[d.to] = data.__types__[d.from];
                delete data.__types__[d.from];
                _.each(data, (row) => {
                    row[d.to] = row[d.from];
                    delete row[d.from];
                });
            });

            let columns = _.keys(data.__types__);
            this.parametersView.setData(data, columns);
            this.updateComponent();
        });

        return this;
    }
});

export default CandelaWidget;
