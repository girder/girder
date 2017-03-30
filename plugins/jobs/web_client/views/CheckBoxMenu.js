import _ from 'underscore';
import View from 'girder/views/View';
import JobCheckBoxMenuTemplate from '../templates/jobCheckBoxMenu.pug';

var CheckBoxMenu = View.extend({
    events: {
        'click input.g-job-filter-checkbox': function (e) {
            _.keys(this.values).forEach(key => {
                if (e.target.id === key) {
                    this.values[key] = e.target.checked;
                }
            });
            this.checkAllChecked = this.allItemChecked();
            this.render();
            this.trigger('g:triggerCheckBoxMenuChanged', this.values);
        },
        'click input.g-job-filter-checkall': function (e) {
            var checked = !this.allItemChecked();
            this.checkAllChecked = checked;
            _.keys(this.values).forEach(key => {
                this.values[key] = checked;
            });
            this.render();
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
    },
    setValues: function (values) {
        this.values = values;
        this.checkAllChecked = this.allItemChecked();
        this.render();
    },
    allItemChecked: function () {
        return _.find(_.keys(this.values), key => !this.values[key]) === undefined;
    }
});

export default CheckBoxMenu;
