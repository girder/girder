import _ from 'underscore';

import View from 'girder/views/View';

import * as vega from '@candela/vega';
import * as treeheatmap from '@candela/treeheatmap';

import { loader, read, inferTypes } from 'vega-loader';

import CandelaWidgetTemplate from '../templates/candelaWidget.pug';
import '../stylesheets/candelaWidget.styl';

import CandelaParametersView from './CandelaParametersView';

const components = Object.assign({}, vega, treeheatmap);

var CandelaWidget = View.extend({
    events: {
        'change .g-item-candela-component': 'updateComponent'
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this._components = _.keys(_.pick(components, (comp) => comp.options));

        this.listenTo(this.item, 'change', function () {
            this.render();
        }, this);

        this.parametersView = new CandelaParametersView({
            component: components[this.$('.g-item-candela-component').val()],
            parentView: this
        });

        this.loader = loader();
        this.render();
    },

    updateComponent: function () {
        this.parametersView.setComponent(components[this.$('.g-item-candela-component').val()]);
    },

    render: function () {
        let options = {
            type: null
        };
        let name = this.item.get('name').toLowerCase();
        if (name.endsWith('.csv')) {
            options.type = 'csv';
        } else if (name.endsWith('.tsv') || name.endsWith('.tab')) {
            options.type = 'tsv';
        } else {
            this.$('.g-item-candela').remove();
            return this;
        }

        this.$el.html(CandelaWidgetTemplate({
            components: this._components
        }));
        this.parametersView.setElement(this.$('.g-item-candela-parameters'));
        this.loader.load(this.item.downloadUrl()).then((data) => {
            data = read(data, options);
            let columns = Object.keys(data[0]);
            const types = inferTypes(data, columns);
            data.__types__ = types;

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

            columns = Object.keys(data[0]);

            this.parametersView.setData(data, columns);
            this.updateComponent();

            return undefined;
        });

        return this;
    }
});

export default CandelaWidget;
