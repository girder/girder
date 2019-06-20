import { sprintf } from 'sprintf-js';

import View from '@girder/core/views/View';

import TaskProgressTemplate from '@girder/core/templates/widgets/taskProgress.pug';

import '@girder/core/stylesheets/widgets/taskProgress.styl';

/**
 * This widget renders the state of a progress notification.
 */
var TaskProgressWidget = View.extend({

    initialize: function (settings) {
        this.progress = settings.progress;
    },

    render: function () {
        var width = '0', barClass = [], progressClass = [], percentText = '',
            timeLeftText = '';

        if (this.progress.data.state === 'active') {
            if (this.progress.data.total <= 0) {
                width = '100%';
                barClass.push('progress-bar-warning');
                progressClass.push('progress-striped', 'active');
            } else if (this.progress.data.current <= 0) {
                width = '0';
                percentText = '0%';
            } else if (this.progress.data.current >= this.progress.data.total) {
                percentText = width = '100%';
            } else {
                var percent = (100 * this.progress.data.current /
                    this.progress.data.total);
                width = Math.round(percent) + '%';
                percentText = percent.toFixed(1) + '%';
                var timeLeft = parseInt(this.progress.estimatedTotalTime - (
                    this.progress.updatedTime - this.progress.startTime), 10);
                if (timeLeft >= 3600) {
                    timeLeftText = sprintf('%d:%02d:%02d left',
                        timeLeft / 3600, (timeLeft / 60) % 60, timeLeft % 60);
                } else if (timeLeft > 0) {
                    timeLeftText = sprintf('%d:%02d left',
                        timeLeft / 60, timeLeft % 60);
                }
            }
        } else if (this.progress.data.state === 'success') {
            width = '100%';
            barClass.push('progress-bar-success');

            this._scheduleHide(5000);
        } else if (this.progress.data.state === 'error') {
            width = '100%';
            barClass.push('progress-bar-danger');

            this._scheduleHide(10000);
        }

        this.$el.html(TaskProgressTemplate({
            progress: this.progress,
            width: width,
            barClass: barClass.join(' '),
            progressClass: progressClass.join(' '),
            percentText: percentText,
            timeLeftText: timeLeftText
        }));
        return this;
    },

    /**
     * Renders an update of the progress object.
     */
    update: function (progress) {
        this.progress = progress;
        this.render();
    },

    /**
     * Schedule a hide event to be triggered in the future.
     */
    _scheduleHide: function (ms) {
        window.setTimeout(() => {
            this.$el.fadeOut(500, () => {
                this.remove();
                this.trigger('g:hide', this.progress);
            });
        }, ms);
    }
});

export default TaskProgressWidget;
