girder.views.jobs = girder.views.jobs || {};
girder.views.jobs.CheckBoxMenuWidget = girder.View.extend({
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
        this.$el.html(girder.templates.jobs_checkBoxMenu(this.params));
    },
    setValues: function (values) {
        this.params.values = values;
        this.render();
    }
});
