import $ from 'jquery';

import View from 'girder/views/View';

import panel from '../templates/panel.pug';
import '../stylesheets/panel.styl';

var Panel = View.extend({
    events: {
        'show.bs.collapse': 'expand',
        'hide.bs.collapse': 'collapse',
        'click .g-panel-title-container': '_handleTitleClick'
    },
    initialize: function (settings) {
        this.spec = settings.spec;
    },
    render: function () {
        this.$el.html(panel(this.spec));

        // initialize collapsible elements
        this.$('.g-panel-content').collapse({toggle: false});

        return this;
    },
    expand: function () {
        this.$('.icon-down-open').attr('class', 'icon-up-open');
    },
    collapse: function () {
        this.$('.icon-up-open').attr('class', 'icon-down-open');
    },
    _handleTitleClick: function (e) {
        if (!$(e.target).hasClass('g-remove-panel')) {
            e.stopPropagation();
            this.$('.g-panel-content').collapse('toggle');
        }
    }
});

export default Panel;
