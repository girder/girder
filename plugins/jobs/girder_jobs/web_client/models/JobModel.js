import _ from 'underscore';

import AccessControlledModel from '@girder/core/models/AccessControlledModel';

import JobStatus from '../JobStatus';

var JobModel = AccessControlledModel.extend({
    resourceName: 'job',

    /**
    * Based on the timestamps fields of the job to
    * calculate how long did each status take. Basically, elapsed of status n
    * equals n+1.time - n.time
    */
    calculateSegmentation: function () {
        var segments = [];

        let timestamps = this.get('timestamps');

        if (timestamps && timestamps.length) {
            let startTime = this.get('created');
            segments.push({
                start: startTime,
                end: timestamps[0].time,
                status: 'Inactive',
                elapsed: this._calculateElapsed(startTime, timestamps[0].time)
            });

            segments = segments.concat(_.map(timestamps.slice(0, -1), (stamp, i) => {
                return {
                    start: stamp.time,
                    end: timestamps[i + 1].time,
                    status: JobStatus.text(stamp.status),
                    elapsed: this._calculateElapsed(stamp.time, timestamps[i + 1].time)
                };
            }));
        }

        return segments;
    },

    _calculateElapsed: function (start, end) {
        return new Date(end) - new Date(start);
    }
});

export default JobModel;
