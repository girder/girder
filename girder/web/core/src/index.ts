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

// This will be modified dynamically when plugins are loaded.
var plugins = {};

export type GirderPackageInfo = {
    girderPlugin?: {
        dependencies?: string[];
    };
};

const extractPackageName = (path: string) => {
    const match = /^\/node_modules\/(.*?)girder-plugin-(.*?)\//g.exec(path);
    if (!match) {
        return null;
    }
    return `${match[1]}girder-plugin-${match[2]}`;
}

const loadPlugins = async (modules: Record<string, () => Promise<unknown>>, packageInfo: Record<string, GirderPackageInfo>) => {
    const pluginModules: Record<string, () => Promise<unknown>> = {};
    for (const path in modules) {
        const plugin = modules[path];
        const name = extractPackageName(path);
        if (!name) {
            console.error(`Problem parsing module name from path: ${path}`)
            continue;
        }
        pluginModules[name] = plugin;
    }

    const dependencyList: [string, string][] = [];
    for (const path in packageInfo) {
        const info = packageInfo[path];
        const name = extractPackageName(path);
        if (!name) {
            console.error(`Problem parsing module name from path: ${path}`)
            continue;
        }
        if (info && info.girderPlugin && info.girderPlugin.dependencies) {
            info.girderPlugin.dependencies.forEach((dependency) => {
                dependencyList.push([name, dependency]);
            });
        }
    }

    // TODO: Use toposort library. For now it's a random order.
    const toposort = (nodes: string[], links: [string, string][]) => {
        return Array.from(new Set([...nodes, ...links.flat(1)]));
    }
    const sortedDependencies = toposort(Object.keys(pluginModules), dependencyList);

    for (const name of sortedDependencies) {
        if (pluginModules[name] === undefined) {
            console.error(`Required module ${name} not found`);
            continue;
        }
        await pluginModules[name]();
    }
};

const initializeDefaultApp = async () => {
    return new Promise((resolve, reject) => {
        $(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const apiRoot = urlParams.get('apiRoot');
            rest.setApiRoot(apiRoot ? decodeURIComponent(apiRoot) : 'http://localhost:8080/api/v1');
            events.trigger('g:appload.before');
            rest.restRequest({
                url: `system/public_settings`,
                method: 'GET',
            }).done((resp: any) => {
                const app = new views.App({
                    el: 'body',
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
    loadPlugins,
    initializeDefaultApp,
    auth,
    collections,
    constants,
    dialog,
    events,
    misc,
    models,
    plugins,
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
