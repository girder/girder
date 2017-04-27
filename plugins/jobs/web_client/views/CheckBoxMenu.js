import _ from 'underscore';
import View from 'girder/views/View';
import JobCheckBoxMenuTemplate from '../templates/jobCheckBoxMenu.pug';
import JobCheckBoxContentTemplate from '../templates/jobCheckBoxContent.pug';

var CheckBoxMenu = View.extend({
    events: {
        'click input.g-job-filter-checkbox': function (e) {
            e.stopPropagation();
            this.items[e.target.id] = e.target.checked;
            this._renderContent();
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
            var checked = !this.allItemChecked();
            _.keys(this.items).forEach(key => {
                this.items[key] = checked;
            });
            this._renderContent();
            this.trigger('g:triggerCheckBoxMenuChanged', this.items);
        }
    },
    initialize: function (params) {
        this.params = params;
        this.items = this.params.items;
    },

    render: function () {
        this.$el.html(JobCheckBoxMenuTemplate({
            title: this.params.title
        }));
        this._renderContent();
    },
    setItems: function (items) {
        this.items = items;
        this._renderContent();
    },
    allItemChecked: function () {
        return _.every(_.values(this.items));
    },
    _renderContent: function () {
        this.$('.dropdown-menu').html(JobCheckBoxContentTemplate({
            items: this.items,
            checkAllChecked: this.allItemChecked()
        }));
    }
});

export default CheckBoxMenu;
