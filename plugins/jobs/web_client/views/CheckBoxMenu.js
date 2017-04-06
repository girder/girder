import _ from 'underscore';
import View from 'girder/views/View';
import JobCheckBoxMenuTemplate from '../templates/jobCheckBoxMenu.pug';
import jobCheckBoxContentTemplate from '../templates/jobCheckBoxContent.pug';

var CheckBoxMenu = View.extend({
    events: {
        'click input.g-job-filter-checkbox': function (e) {
            e.stopPropagation();
            _.keys(this.values).forEach(key => {
                if (e.target.id === key) {
                    this.values[key] = e.target.checked;
                }
            });
            this.checkAllChecked = this.allItemChecked();
            this._renderContent();
            this.trigger('g:triggerCheckBoxMenuChanged', this.values);
        },
        // When a label wrap a input and the label is clicked, there will be two event being triggered, stop the first one from bubbling up to prevent unexpected behavior
        'click label': function (e) {
            e.stopPropagation();
        },
        'click .dropdown-menu': e => {
            e.stopPropagation();
        },
        'click .g-job-checkall input': function (e) {
            e.stopPropagation();
            var checked = !this.allItemChecked();
            this.checkAllChecked = checked;
            _.keys(this.values).forEach(key => {
                this.values[key] = checked;
            });
            this._renderContent();
            this.trigger('g:triggerCheckBoxMenuChanged', this.values);
        }
    },
    initialize: function (params) {
        this.params = params;
        this.checkAllChecked = true;
        this.values = this.params.values;
    },

    render: function () {
        this.$el.html(JobCheckBoxMenuTemplate({
            title: this.params.title,
            values: this.values,
            checkAllChecked: this.checkAllChecked
        }));
        this._renderContent();
    },
    setValues: function (values) {
        this.values = values;
        this.checkAllChecked = this.allItemChecked();
        this._renderContent();
    },
    allItemChecked: function () {
        return _.find(_.keys(this.values), key => !this.values[key]) === undefined;
    },
    _renderContent: function () {
        this.$('.dropdown-menu').html(jobCheckBoxContentTemplate(this));
    }
});

export default CheckBoxMenu;
