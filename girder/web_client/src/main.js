import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import moment from 'moment';
import * as girder from '@girder/core';
import { setApiRoot, restRequest } from '@girder/core/rest';

// Hack for now to get SPA working from a different port
setApiRoot('http://localhost:8080/api/v1');

window.girder = girder;

// Some cross-browser globals
if (!window.console) {
    window.console = {
        log: $.noop,
        error: $.noop
    };
}

// For testing and convenience, available now because of testUtils.js reliance on $
window.$ = $;
window._ = _;
window.moment = moment;
window.Backbone = Backbone;

// Do the actual app spinup here instead of in the mako template served by girder server
$(function () {
    girder.events.trigger('g:appload.before');
    restRequest({
        url: `system/public_settings`,
        method: 'GET'
    }).done((resp) => {
        const app = new girder.views.App({
            el: 'body',
            parentView: null,
            contactEmail: resp['core.contact_email_address'],
            privacyNoticeHref: resp['core.privacy_notice'],
            brandName: resp['core.brand_name'],
            bannerColor: resp['core.banner_color'],
            registrationPolicy: resp['core.registration_policy'],
            enablePasswordLogin: resp['core.enable_password_login'],
        }).render();
        girder.events.trigger('g:appload.after', app);
    }).fail((resp) => {
        girder.events.trigger('g:error', resp);
    });
});
