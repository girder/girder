import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import router from '@girder/core/router';
import { parseQueryString, splitRoute } from '@girder/core/misc';

import ConfirmDialogTemplate from '@girder/core/templates/widgets/confirmDialog.pug';

import '@girder/core/utilities/jquery/girderModal';

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
 * @param {Object} [params] Parameters controlling this function's behavior.
 * @param {String} [params.text] The text to prompt the user with.
 * @param {String} [params.yesText] The text for the confirm button.
 * @param {String} [params.yesClass] Class string to apply to the confirm button.
 * @param {String} [params.noText] The text for the no/cancel button.
 * @param {Boolean} [params.escapedHtml] If you want to render the text as HTML rather than
 *        plain text, set this to true to acknowledge that you have escaped any
 *        user-created data within the text to prevent XSS exploits.
 * @param {Boolean} [params.msgConfirmation] If you want to add a new security before
 *        perform an action. This will ask to enter a specific string "params.yesText params.name"
 * @param {String} [params.additionalText] Additional text to display before the confirmation
 *        input.
 * @param {String} [params.name] The name to enter in order to confirm an action.
 * @param {Function} [params.confirmCallback]Callback function when the user confirms the action.
 */
function confirm(params) {
    params = _.extend({
        text: 'Are you sure?',
        yesText: 'Yes',
        yesClass: 'btn-danger',
        noText: 'Cancel',
        escapedHtml: false,
        msgConfirmation: false,
        additionalText: '',
        name: ''
    }, params);
    $('#g-dialog-container').html(ConfirmDialogTemplate({
        params: params
    })).girderModal(false).one('hidden.bs.modal', function () {
        $('#g-confirm-button').off('click');
    });

    const el = $('#g-dialog-container').find('.modal-body>p:first-child');
    if (params.escapedHtml) {
        el.html(params.text);
    } else {
        el.text(params.text);
    }
    if (params['msgConfirmation']) {
        if (params.escapedHtml) {
            $('.g-additional-text').html(params.additionalText);
        } else {
            $('.g-additional-text').text(params.additionalText);
        }
    }

    $('#g-confirm-button').off('click').click(function () {
        if (params['msgConfirmation']) {
            const key = `${params.yesText.toUpperCase()} ${params.name}`;
            const msg = $('#g-confirm-text').val();
            if (msg.toUpperCase() === key.toUpperCase()) {
                $('#g-dialog-container').modal('hide');
                params.confirmCallback();
            } else if (msg.toUpperCase() === '') {
                $('.g-msg-error').html(`Error: You need to enter <b>'${key}'</b>.`);
                $('.g-msg-error').css('color', 'red');
            } else {
                $('.g-msg-error').html(`Error: <b>'${msg}'</b> isn't <b>'${key}'</b>`);
                $('.g-msg-error').css('color', 'red');
            }
        } else {
            $('#g-dialog-container').modal('hide');
            params.confirmCallback();
        }
    });
}

export {
    confirm,
    handleClose,
    handleOpen
};
