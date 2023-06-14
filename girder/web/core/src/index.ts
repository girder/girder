import * as auth from './auth';
import * as collections from './collections';
import * as constants from './constants';
import * as dialog from './dialog';
import * as misc from './misc';
import * as models from './models';
import * as rest from './rest';
import * as utilities from './utilities';
import * as views from './views';
import events from './events';
import router from './router';
import version from './version';
import $ from 'jquery';

// This will be modified dynamically when plugins are loaded.
var plugins = {};

export type GirderPlugin = {
    init: (girder: any) => void;
    dependencies?: string[];
};

const loadPlugins: (modules: {[name: string]: GirderPlugin}, girder: any) => void = (modules, girder) => {
    const dependencyList: [string, string][] = [];
    const pluginModules: {[name: string]: GirderPlugin} = {};
    for (const path in modules) {
        const plugin = modules[path];
        const match = /^\/node_modules\/(.*)girder-plugin-(.*)\//g.exec(path);
        if (!match) {
            console.error(`Problem parsing module name from path: ${path}`)
            continue;
        }
        const name = `${match[1]}girder-plugin-${match[2]}`;
        pluginModules[name] = plugin;
        if (plugin.dependencies) {
            plugin.dependencies.forEach((dependency) => {
                dependencyList.push([name, dependency])
            });
        }
    }

    // TODO: use toposort library
    const toposort = (list: [string, string][]) => {
        const nodes = Array.from(new Set(list.flat(1)));
        return nodes;
    }

    const sortedDependencies = toposort(dependencyList);
    sortedDependencies.forEach((name) => {
        if (pluginModules[name] === undefined) {
            console.error(`Required module ${name} not found`);
            return;
        }
        pluginModules[name].init(girder);
    });
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

export {
    $,
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
    rest,
    router,
    utilities,
    version,
    views
};

// type Girder = typeof girder;
