import $ from 'jquery';

import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import events from 'girder/events';

import candela from 'girder_plugins/candela/node/candela';
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
        this._components = [];
        for (let component in candela.components) {
            if (candela.components.hasOwnProperty(component)) {
                this._components.push(component);
            }
        }

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
        if (this.accessLevel >= AccessType.READ && this.item.get('name').toLowerCase().endsWith('.csv')) {
            this.$el.html(CandelaWidgetTemplate({
                components: this._components
            }));
            this.parametersView.setElement($('.g-item-candela-parameters'));
            datalib.csv(this.item.downloadUrl(), (error, data) => {
                if (error) {
                    let info = {
                        text: 'An error occurred while attempting to read and ' +
                              'parse the data file. Details have been logged in the console.',
                        type: 'danger',
                        timeout: 5000,
                        icon: 'attention'
                    };
                    events.trigger('g:alert', info);
                    console.error(error);
                    return;
                }

                datalib.read(data, {parse: 'auto'});

                // Vega has issues with empty-string fields and fields with dots, so rename those.
                let rename = [];
                for (let key in data.__types__) {
                    if (data.__types__.hasOwnProperty(key)) {
                        if (key === '') {
                            rename.push(['', 'id']);
                        } else if (key.indexOf('.') >= 0) {
                            rename.push([key, key.replace(/\./g, '_')]);
                        }
                    }
                }

                rename.forEach((d) => {
                    data.__types__[d[1]] = data.__types__[d[0]];
                    delete data.__types__[d[0]];
                    data.forEach((row) => {
                        row[d[1]] = row[d[0]];
                        delete row[d[0]];
                    });
                });

                let columns = [];
                for (let key in data.__types__) {
                    if (data.__types__.hasOwnProperty(key)) {
                        columns.push(key);
                    }
                }
                this.parametersView.setData(data, columns);
                this.updateComponent();
            });
        } else {
            this.$('.g-item-candela')
                .remove();
        }
    }
});

export default CandelaWidget;
