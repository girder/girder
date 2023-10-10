import $ from 'jquery';

/**
 * Helper selector to enable/disable inputs elements
 *
 * @param enable Whether to enable the element or not
 */
$.fn.girderEnable = function (enable) {
    var selection = $(this);
    if (selection.is(':input')) {
        selection.prop('disabled', !enable);
    }
    if (!enable) {
        selection.addClass('disabled');
    } else {
        selection.removeClass('disabled');
    }
    return this;
};
