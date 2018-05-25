import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import taskStatusViewTemplate from '../templates/taskStatusView.pug';

var taskStatusView = View.extend({
    events: {
        'click .g-worker-status-btn-reload': function () {
            this._fetchWorkerStatus();
        },
        'click .g-worker-task-status-link': function (e) {
            var row = e.target.parentElement;
            var workerName = row.childNodes[0].innerText;
            _.each(this.workers, (worker) => {
                if (worker['name'] === workerName) {
                    this.workerName = workerName;
                    this.activeTaskList = worker['active'];
                    this.reservedTaskList = worker['reserved'];
                    this.render();
                }
            });
        }
    },

    initialize: function () {
        this.errorMsg = null;
        this._fetchWorkerStatus();
    },

    render: function () {
        this.$el.html(taskStatusViewTemplate({
            workerList: this.workers,
            load: this.load,
            workerName: this.workerName,
            activeTasks: this.activeTaskList,
            reservedTasks: this.reservedTaskList,
            errorMsg: this.errorMsg
        }));

        return this;
    },

    _fetchWorkerStatus: function () {
        this.workers = [];
        this.activeTaskList = [];
        this.reservedTaskList = [];
        this.load = true;
        restRequest({
            method: 'GET',
            url: 'worker/status'
        }).done((resp) => {
            if (resp === -1) {
                this.errorMsg = 'The Broker is inaccessible.';
            } else {
                this.errorMsg = null;
                this.parseWorkerStatus(
                    resp.report,
                    resp.stats,
                    resp.ping,
                    resp.active,
                    resp.reserved);
            }
            this.load = false;
            this.render();
        });

        this.render();
    },

    parseWorkerStatus: function (report, stats, ping, active, reserved) {
        var workers = _.keys(report);
        var reportTmp = null;
        var statsTmp = null;
        var concurrencyTmp = null;
        var pingTmp = null;
        _.each(workers, (worker) => {
            if (_.has(report[worker], 'ok')) {
                reportTmp = report[worker]['ok'];
            }
            if (stats[worker]['total'] !== null) {
                statsTmp = _.values(stats[worker]['total'])[0];
            }
            if (stats[worker]['pool'] !== null) {
                concurrencyTmp = stats[worker]['pool']['max-concurrency'];
            }
            if (_.has(ping[worker], 'ok')) {
                pingTmp = ping[worker]['ok'];
            }
            this.workers.push({
                'name': worker,
                'report': reportTmp,
                'stats': statsTmp | 0,
                'concurrency': concurrencyTmp | 0,
                'ping': pingTmp,
                'active': active[worker],
                'reserved': reserved[worker]
            });
        });
        if (!this.workers.length) {
            this.errorMsg = 'No task information.';
        }
    }
});

export default taskStatusView;
