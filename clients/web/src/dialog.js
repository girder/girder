import $ from 'jquery';
import Backbone from 'backbone';

import router from 'girder/router';
import { parseQueryString, splitRoute } from 'girder/misc';

import ConfirmDialogTemplate from 'girder/templates/widgets/confirmDialog.pug';

import 'girder/utilities/jquery/girderModal';

function handleClose(name, options, nameId) {
    if (!router.enabled()) {
        return;
    }
    var curRoute = Backbone.history.fragment,
        routeParts = splitRoute(curRoute),
        queryString = parseQueryString(routeParts.name),
        dialogName = queryString.dialog,
        dialogId = queryString.dialogid;
    delete queryString.dialog;
    delete queryString.dialogid;
    var unparsedQueryString = $.param(queryString);
    if (unparsedQueryString.length > 0) {
        unparsedQueryString = '?' + unparsedQueryString;
    }
    if (dialogName === name && dialogId === nameId) {
        router.navigate(routeParts.base + unparsedQueryString, options);
    }
}

function handleOpen(name, options, nameId) {
    if (!router.enabled()) {
        return;
    }
    var curRoute = Backbone.history.fragment,
        routeParts = splitRoute(curRoute),
        queryString = parseQueryString(routeParts.name),
        dialogName = queryString.dialog,
        dialogId = queryString.dialogid;

    if (dialogName !== name || nameId !== dialogId) {
        queryString.dialog = name;
        if (nameId) {
            queryString.dialogid = nameId;
        }
        var unparsedQueryString = $.param(queryString);
        if (unparsedQueryString.length > 0) {
            unparsedQueryString = '?' + unparsedQueryString;
        }
        router.navigate(routeParts.base + unparsedQueryString, options);
    }
}

/**
 * Prompt the user to confirm an action.
 * @param [text] The text to prompt the user with.
 * @param [yesText] The text for the confirm button.
 * @param [yesClass] Class string to apply to the confirm button.
 * @param [noText] The text for the no/cancel button.
 * @param [escapedHtml] If you want to render the text as HTML rather than
 *        plain text, set this to true to acknowledge that you have escaped any
 *        user-created data within the text to prevent XSS exploits.
 * @param confirmCallback Callback function when the user confirms the action.
 */
function confirm(params) {
    params = _.extend({
        text: 'Are you sure?',
        yesText: 'Yes',
        yesClass: 'btn-danger',
        noText: 'Cancel',
        escapedHtml: false
    }, params);
    $('#g-dialog-container').html(ConfirmDialogTemplate({
        params: params
    })).girderModal(false);

    var el = $('#g-dialog-container').find('.modal-body>p');
    if (params.escapedHtml) {
        el.html(params.text);
    } else {
        el.text(params.text);
    }

    $('#g-confirm-button').unbind('click').click(function () {
        $('#g-dialog-container').modal('hide');
        params.confirmCallback();
    });
}

export {
    confirm,
    handleClose,
    handleOpen
};
