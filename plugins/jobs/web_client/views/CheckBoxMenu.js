import View from 'girder/views/View';
import JobCheckBoxMenuTemplate from '../templates/jobCheckBoxMenu.pug';

var CheckBoxMenu = View.extend({
    events: {
        'click input': function (e) {
            var checkBoxStates = {};
            $.each(this.$('input'), function (i, input) {
                checkBoxStates[input.id] = input.checked;
            });
            this.trigger('g:triggerCheckBoxMenuChanged', checkBoxStates);
        }
    },
    initialize: function (params) {
        this.params = params;
        this.dropdownToggle = params.dropdownToggle;
    },

    render: function () {
        this.$el.html(JobCheckBoxMenuTemplate(this.params));
    },
    setValues: function (values) {
        this.params.values = values;
        this.render();
    }
});

export default CheckBoxMenu;
