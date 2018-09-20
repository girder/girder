import $ from 'jquery';
import _ from 'underscore';

import { parse,
    View as VegaView } from 'vega-lib';

import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { restRequest } from 'girder/rest';

import VegaWidgetTemplate from '../templates/vegaWidget.pug';
import '../stylesheets/vegaWidget.styl';

var VegaWidget = View.extend({
    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this.item.on('change', function () {
            this.render();
        }, this);
        this.render();
    },

    render: function () {
        var meta = this.item.get('meta');

        if (this.accessLevel >= AccessType.READ && meta && meta.vega) {
            $('#g-app-body-container')
                .append(VegaWidgetTemplate());
            restRequest({
                url: `item/${this.item.id}/download`
            })
                .done(_.bind(function (spec) {
                    let runtime = parse(spec);
                    let view = new VegaView(runtime)
                        .initialize($('.g-item-vega-vis')[0])
                        .renderer('svg');
                    view.run();
                }, this));
        } else {
            $('.g-item-vega')
                .remove();
        }

        return this;
    }
});

export default VegaWidget;
