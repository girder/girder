import $ from 'jquery';

// $.when behave differently with zero, one or more argument. This helper method minics Promise.all() behavior
$.whenAll = function (promises) {
    return $.when(...promises).then((...results) => results);
};
