import $ from 'jquery';

import vg from 'vega';

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
                path: '/api/v1/item/' + this.item.get('_id') + '/download'
            })
                .done(function (spec) {
                    vg.parse.spec(spec, function (chart) {
                        chart({
                            el: '.g-item-vega-vis',
                            renderer: 'svg'
                        }).update();
                    });
                });
        } else {
            $('.g-item-vega')
                .remove();
        }

        return this;
    }
});

export default VegaWidget;
