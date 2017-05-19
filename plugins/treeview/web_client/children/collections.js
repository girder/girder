import _ from 'underscore';

import request from '../utils/request';
import { collection } from '../types';

export default function () {
    return request({
        path: 'collection'
    }).then((collections) => {
        return _.map(collections, collection);
    });
}
