import _ from 'underscore';

import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';

import ConfigTemplate from '../templates/configView.pug';

import ConfigView from '@girder/worker/views/ConfigView';

wrap(ConfigView, 'render', function (render) {
    render.call(this);

    this.$("p#g-worker-settings-error-message", "#g-worker-settings-form").before(
        ConfigTemplate()
    );

    return this;
});

wrap(ConfigView, 'initialize', function (initialize) {
    initialize.call(this);

    restRequest({
        method: 'GET',
        url: 'system/setting',
        data: {
            list: JSON.stringify([
                'worker_slurm.account',
                'worker_slurm.qos',
                'worker_slurm.mem',
                'worker_slurm.cpus',
                'worker_slurm.ntasks',
                'worker_slurm.partition',
                'worker_slurm.time',
                'worker_slurm.gres_config',
                'worker_slurm.gpu',
                'worker_slurm.gpu_partition'
            ])
        }
    }).done((resp) => {
        this.$('#g-worker-slurm-account').val(resp['worker_slurm.account']);
        this.$('#g-worker-slurm-qos').val(resp['worker_slurm.qos']);
        this.$('#g-worker-slurm-mem').val(resp['worker_slurm.mem']);
        this.$('#g-worker-slurm-cpu').val(resp['worker_slurm.cpus']);
        this.$('#g-worker-slurm-ntasks').val(resp['worker_slurm.ntasks']);
        this.$('#g-worker-slurm-partition').val(resp['worker_slurm.partition']);
        this.$('#g-worker-slurm-time').val(resp['worker_slurm.time']);
        this.$('#g-worker-slurm-gres-config').val(resp['worker_slurm.gres_config']);
        this.$('#g-worker-slurm-gpu').val(resp['worker_slurm.gpu']);
        this.$('#g-worker-slurm-gpu-partition').val(resp['worker_slurm.gpu_partition']);
    });
});

const workerConfigSubmitEvent = ConfigView.prototype.events['submit #g-worker-settings-form'];
ConfigView.prototype.events['submit #g-worker-settings-form'] = function (event) {
    workerConfigSubmitEvent.call(this, event);

    this._saveSettings([{
        key: 'worker_slurm.account',
        value: this.$('#g-worker-slurm-account').val().trim()
    }, {
        key: 'worker_slurm.qos',
        value: this.$('#g-worker-slurm-qos').val().trim()
    }, {
        key: 'worker_slurm.mem',
        value: this.$('#g-worker-slurm-mem').val().trim()
    }, {
        key: 'worker_slurm.cpus',
        value: this.$('#g-worker-slurm-cpu').val().trim()
    }, {
        key: 'worker_slurm.ntasks',
        value: this.$('#g-worker-slurm-ntasks').val().trim()
    }, {
        key: 'worker_slurm.partition',
        value: this.$('#g-worker-slurm-partition').val().trim()
    }, {
        key: 'worker_slurm.time',
        value: this.$('#g-worker-slurm-time').val().trim()
    }, {
        key: 'worker_slurm.gres_config',
        value: this.$('#g-worker-slurm-gres-config').val().trim()
    }, {
        key: 'worker_slurm.gpu',
        value: this.$('#g-worker-slurm-gpu').val().trim()
    }, {
        key: 'worker_slurm.gpu_partition',
        value: this.$('#g-worker-slurm-gpu-partition').val().trim()
    }]);
};
