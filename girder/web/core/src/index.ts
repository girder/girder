import * as auth from './auth';
import * as collections from './collections';
import * as constants from './constants';
import * as dialog from './dialog';
import * as misc from './misc';
import * as models from './models';
import * as pluginUtils from './pluginUtils';
import * as rest from './rest';
import * as utilities from './utilities';
import * as views from './views';
import events from './events';
import router from './router';
import version from './version';
import $ from 'jquery';
import _ from 'underscore';
import moment from 'moment';

const initializeDefaultApp = async (apiRoot: string, el: string | HTMLElement = 'body') => {
    return new Promise((resolve, reject) => {
        $(() => {
            rest.setApiRoot(apiRoot);
            events.trigger('g:appload.before');
            rest.restRequest({
                url: `system/public_settings`,
                method: 'GET',
            }).done((resp: any) => {
                const app = new views.App({
                    el,
                    parentView: null,
                    contactEmail: resp['core.contact_email_address'],
                    privacyNoticeHref: resp['core.privacy_notice'],
                    brandName: resp['core.brand_name'],
                    bannerColor: resp['core.banner_color'],
                    registrationPolicy: resp['core.registration_policy'],
                    enablePasswordLogin: resp['core.enable_password_login'],
                });
                app.render();
                document.title = resp['core.brand_name'];
                events.trigger('g:appload.after', app);
                resolve(app);
            }).fail((resp: any) => {
                events.trigger('g:error', resp);
                reject(null);
            });
        });
    });
};

const girder = {
    $,
    _,
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
    utilities,
    version,
    views
};

export type Girder = typeof girder;

export {
    girder,
};
