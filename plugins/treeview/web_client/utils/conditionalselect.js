import _ from 'underscore';

export default function (selectable) {
    if (_.isFunction(selectable)) {
        return selectable;
    }

    if (_.isArray(selectable)) {
        return function (model) {
            return model && _.contains(selectable, model._modelType);
        };
    }

    return function (model) {
        return model;
    };
}
