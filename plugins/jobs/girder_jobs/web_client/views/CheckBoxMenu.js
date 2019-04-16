import _ from 'underscore';

import View from '@girder/core/views/View';

import JobCheckBoxMenuTemplate from '../templates/jobCheckBoxMenu.pug';
import JobCheckBoxContentTemplate from '../templates/jobCheckBoxContent.pug';

var CheckBoxMenu = View.extend({
    events: {
        'click input.g-job-filter-checkbox': function (e) {
            e.stopPropagation();
            this.items[e.target.id] = e.target.checked;
            this.trigger('g:triggerCheckBoxMenuChanged', this.items);
        },
        // When a label wraps an input and the label is clicked,
        // there will be two events being triggered,
        // stop the first one from bubbling up to prevent unexpected behavior
        'click label': function (e) {
            e.stopPropagation();
        },
        'click .dropdown-menu': function (e) {
            e.stopPropagation();
        },
        'click .g-job-checkall input': function (e) {
            e.stopPropagation();
            // If any are unchecked, set all to checked; if all are checked, set all to unchecked
            var newCheckedState = !this._allItemsChecked();
            _.keys(this.items).forEach((key) => {
                this.items[key] = newCheckedState;
            });
            this.trigger('g:triggerCheckBoxMenuChanged', this.items);
        }
    },

    initialize: function (params) {
        this.params = params;
        this.items = this.params.items;
        this.on('g:triggerCheckBoxMenuChanged', this._renderContent, this);
    },

    render: function () {
        this.$el.html(JobCheckBoxMenuTemplate({
            title: this.params.title
        }));
        this._renderContent();
        return this;
    },

    setItems: function (items) {
        this.items = items;
        this._renderContent();
    },

    _allItemsChecked: function () {
        return _.every(this.items);
    },

    _anyItemsChecked: function () {
        return _.some(this.items);
    },

    _renderContent: function () {
        this.$('.dropdown-menu').html(JobCheckBoxContentTemplate({
            items: this.items,
            checkAllChecked: this._allItemsChecked()
        }));
    }
});

export default CheckBoxMenu;
