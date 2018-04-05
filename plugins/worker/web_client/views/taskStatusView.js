import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import taskStatusViewTemplate from '../templates/taskStatusView.pug';

var taskStatusView = View.extend({
    events: {
        'click .g-worker-task-status-btn-reload': function () {
            this._fetchWorkerStatus();
        },
        'click .g-worker-task-status-link': function (e) {
            var row = e.target.parentElement;
            var workerName = row.childNodes[0].innerText;
            _.each(this.workers, (worker) => {
                if (worker['name'] === workerName) {
                    this.workerName = workerName;
                    this.activeTaskList = worker['active'];
                    this.render();
                }
            });
        }
    },

    initialize: function () {
        this._fetchWorkerStatus();
    },

    render: function () {
        this.$el.html(taskStatusViewTemplate({
            workerList: this.workers,
            load: this.load,
            workerName: this.workerName,
            activeTasks: this.activeTaskList
        }));

        return this;
    },

    _fetchWorkerStatus: function () {
        this.workers = [];
        this.activeTaskList = [];
        this.load = true;
        restRequest({
            method: 'GET',
            url: 'worker/status'
        }).done((resp) => {
            this.load = false;
            this.parseWorkerStatus(
                resp.report,
                resp.stats,
                resp.ping,
                resp.active,
                resp.queues,
                resp.scheduled);
            this.render();
        });

        this.render();
    },

    parseWorkerStatus: function (report, stats, ping, active, queues, scheduled) {
        var workers = _.keys(report);
        var reportTmp = null;
        var statsTmp = null;
        var pingTmp = null;
        _.each(workers, (worker) => {
            if (_.has(report[worker], 'ok')) {
                reportTmp = report[worker]['ok'];
            }
            if (stats[worker]['total'] !== null) {
                statsTmp = _.values(stats[worker]['total'])[0];
            }
            if (_.has(ping[worker], 'ok')) {
                pingTmp = ping[worker]['ok'];
            }
            this.workers.push({
                'name': worker,
                'report': reportTmp,
                'stats': statsTmp | 0,
                'ping': pingTmp,
                'active': active[worker],
                'queues': queues[worker],
                'scheduled': scheduled[worker]
            });
        });
    }
});

export default taskStatusView;
