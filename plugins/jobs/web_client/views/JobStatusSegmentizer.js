import _ from 'underscore';
import JobStatus from '../JobStatus';

export default class JobStatusSegmentizer {
    segmentize(jobs) {
        for (let job of jobs) {
            var segments = [];

            let timestamps = job.get('timestamps');

            if (timestamps && timestamps.length) {
                let startTime = job.get('created');
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

            job.set('segments', segments);
        }
    }

    _calculateElapsed(start, end) {
        return new Date(end) - new Date(start);
    }
}
