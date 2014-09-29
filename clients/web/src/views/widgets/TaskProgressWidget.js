/**
 * This widget renders the state of a progress notification.
 */
girder.views.TaskProgressWidget = Backbone.View.extend({

    initialize: function (settings) {
        this.progress = settings.progress;
    },

    render: function () {
        var width = '0', barClass = [], progressClass = [];

        if (this.progress.data.state === 'active') {
            if (this.progress.data.total <= 0) {
                width = '100%';
                barClass.push('progress-bar-warning');
                progressClass.push('progress-striped', 'active');
            } else {
                width = Math.round(
                  this.progress.data.current / this.progress.data.total) + '%';
            }
        }
        else if (this.progress.data.state === 'success') {
            width = '100%';
            barClass.push('progress-bar-success');
        }
        else if (this.progress.data.state === 'error') {
            width = '100%';
            barClass.push('progress-bar-danger');
        }

        this.$el.html(jade.templates.taskProgress({
            progress: this.progress,
            width: width,
            barClass: barClass.join(' '),
            progressClass: progressClass.join(' ')
        }));
        return this;
    },

    update: function (progress) {
        this.progress = progress;
        this.render();
    }
});
