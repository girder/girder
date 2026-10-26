import $ from 'jquery';

import _ from 'underscore';

import Backbone from 'backbone';

import moment from 'moment';

import * as auth from './auth';
import * as collections from './collections';
import * as constants from './constants';
import * as dialog from './dialog';
import * as misc from './misc';
import * as models from './models';
import * as pluginUtils from './pluginUtils';
import * as rest from './rest';
import * as uiStyle from './uiStyle';
import * as utilities from './utilities';
import * as views from './views';
import events from './events';
import router from './router';
import version from './version';

const initializeDefaultApp = async (apiRoot: string, el: string | HTMLElement = 'body') => {
    return new Promise((resolve, reject) => {
        $(() => {
            rest.setApiRoot(apiRoot);
            events.trigger('g:appload.before');
            rest.restRequest({
                url: `system/public_settings`,
                method: 'GET',
            }).done((resp: any) => {
                rest.setPublicSettings(resp);
                // Load the stylesheet for the configured style before the
                // app renders so the page does not flash the other look.
                uiStyle.setUiStyle(resp['core.ui_style']).done(() => {
                    const app = new views.App({
                        el,
                        parentView: null,
                        contactEmail: resp['core.contact_email_address'],
                        privacyNoticeHref: resp['core.privacy_notice'],
                        brandName: resp['core.brand_name'],
                        bannerColor: resp['core.banner_color'],
                        registrationPolicy: resp['core.registration_policy'],
                        enablePasswordLogin: resp['core.enable_password_login'],
                        showDownload: resp['core.show_download'],
                        uiStyle: resp['core.ui_style'],
                        headerNavLabel: resp['core.ui_header_nav_label'],
                    });
                    app.render();
                    document.title = resp['core.brand_name'];
                    events.trigger('g:appload.after', app);
                    resolve(app);
                });
            }).fail((resp: any) => {
                events.trigger('g:error', resp);
                reject(new Error("Could not retrieve public settings from server."));
            });
        });
    });
};

const girder = {
    $,
    _,
    Backbone,
    moment,
    initializeDefaultApp,
    auth,
    collections,
    constants,
    dialog,
    events,
    misc,
    models,
    plugins: {},
    pluginUtils,
    rest,
    router,
    uiStyle,
    utilities,
    version,
    views
};

export type Girder = typeof girder;

export {
    girder,
};
