import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

/**
 * Port of the legacy widgetSpec.js "control widget view" and "control widget
 * getRoot" describes. The views need a live Backbone/girder environment, so
 * the assertions run inside the browser against the plugin namespace.
 */
type EvalFn<T> = () => T;

const run = async <T>(page: Page, fn: EvalFn<T>): Promise<T> => page.evaluate(fn);

test.describe('Slicer CLI web control widget view', () => {
    setupServer();

    test.beforeEach(async ({ page }) => {
        await page.evaluate(() => {
            const w = window as any;
            w.__fails = [];
            const show = (v: any) => JSON.stringify(v);
            w.__is = (actual: any, expected: any, msg: string) => {
                if (actual !== expected) {
                    w.__fails.push(`${msg}: expected ${show(expected)} got ${show(actual)}`);
                }
            };
            w.__eq = (actual: any, expected: any, msg: string) => {
                if (show(actual) !== show(expected)) {
                    w.__fails.push(`${msg}: expected ${show(expected)} got ${show(actual)}`);
                }
            };
            w.__match = (actual: any, re: RegExp, msg: string) => {
                if (!re.test(actual)) {
                    w.__fails.push(`${msg}: ${show(actual)} does not match ${re}`);
                }
            };
            w.__checkWidgetCommon = (widget: any) => {
                const model = widget.model;
                w.__is(widget.$(`label[for="${model.id}"]`).text(), model.get('title'), 'label text');
                if (widget.model.isEnumeration()) {
                    w.__is(widget.$(`select#${model.id}`).length, 1, 'select count');
                } else {
                    w.__is(widget.$(`input#${model.id}`).length, 1, 'input count');
                }
            };
            w.__waitFor = (cond: () => boolean, timeout = 5000) => new Promise<void>((resolve, reject) => {
                const start = Date.now();
                const tick = () => {
                    try {
                        if (cond()) {
                            resolve();
                            return;
                        }
                    } catch (err) {
                        reject(err);
                        return;
                    }
                    if (Date.now() - start > timeout) {
                        reject(new Error('__waitFor timeout'));
                        return;
                    }
                    setTimeout(tick, 20);
                };
                tick();
            });
        });
    });

    test('range', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'range', title: 'Title', id: 'range-widget',
                    value: 2, min: 0, max: 10, step: 2,
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').val(), '2', 'range value');
            widget.$('input').val('4').trigger('change');
            w.__is(widget.model.value(), 4, 'range changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('number', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'number', title: 'Title', id: 'number-widget',
                    value: 2, min: 0, max: 10, step: 2,
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').val(), '2', 'number value');
            widget.$('input').val('4').trigger('change');
            w.__is(widget.model.value(), 4, 'number changed value');
            widget.$('input').val('4').trigger('change');
            w.__is(widget.$('.form-group').hasClass('has-error'), false, 'no error');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('boolean', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({ type: 'boolean', title: 'Title', id: 'boolean-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').prop('checked'), false, 'boolean unchecked');
            widget.$('input').click();
            w.__is(widget.model.value(), true, 'boolean checked value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'string', title: 'Title', id: 'string-widget', value: 'default',
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').val(), 'default', 'string value');
            widget.$('input').val('new value').trigger('change');
            w.__is(widget.model.value(), 'new value', 'string changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('color', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'color', title: 'Title', id: 'color-widget', value: 'red',
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.model.value(), '#ff0000', 'color value');
            w.__is(widget.$('input[type="color"]').length, 1, 'color input');
            widget.$('input').val('#ffffff').trigger('change');
            w.__is(widget.model.value(), '#ffffff', 'color changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string-vector', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'string-vector', title: 'Title', id: 'string-vector-widget',
                    value: 'one,two,three',
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').val(), 'one,two,three', 'string-vector value');
            widget.$('input').val('1,2,3').trigger('change');
            w.__eq(widget.model.value(), ['1', '2', '3'], 'string-vector changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('number-vector', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'number-vector', title: 'Title', id: 'number-vector-widget',
                    value: '1,2,3',
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('input').val(), '1,2,3', 'number-vector value');
            widget.$('input').val('10,20,30').trigger('change');
            w.__eq(widget.model.value(), [10, 20, 30], 'number-vector changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string-enumeration', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'string-enumeration', title: 'Title', id: 'string-enumeration-widget',
                    value: 'value 2', values: ['value 1', 'value 2', 'value 3'],
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('select').val(), 'value 2', 'string-enumeration value');
            widget.$('select').val('value 3').trigger('change');
            w.__is(widget.model.value(), 'value 3', 'string-enumeration changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('number-enumeration', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'number-enumeration', title: 'Title', id: 'number-enumeration-widget',
                    value: 200, values: [100, 200, 300],
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('select').val(), '200', 'number-enumeration value');
            widget.$('select').val('300').trigger('change');
            w.__is(widget.model.value(), 300, 'number-enumeration changed value');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('item', async ({ page }) => {
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
            const item = new girder.models.ItemModel({ id: 'model id', name: 'b' });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            let arg: any;
            hProto.initialize = function (_arg: any) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                parentView,
                rootPath: admin,
                el,
                model: new slicer.models.WidgetModel({ type: 'item', title: 'Title', id: 'item-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            widget.$('.s-select-file-button').click();
            w.__is(widget.$('.s-select-multifile-button').length, 1, 'multifile button');
            w.__is(arg.parentModel.get('_id'), admin.get('_id'), 'parentModel is admin');
            arg.onItemClick(item);
            arg.parentView._validate();
            await w.__waitFor(() => widget.model && widget.model.value() && widget.model.value().name() === 'b');
            w.__is(widget.model.value().name(), 'b', 'item value name');
            w.__eq(widget.model.get('path'), [], 'item path');

            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('file', async ({ page }) => {
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
            const item = new girder.models.ItemModel({ _id: 'item id', name: 'd' });
            const file = new girder.models.FileModel({ _id: 'file id', name: 'e' });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            let arg: any;
            hProto.initialize = function (_arg: any) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView,
                el,
                model: new slicer.models.WidgetModel({ type: 'file', title: 'Title', id: 'file-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);

            const origAjax = girder.$.ajax;
            girder.$.ajax = function (opts: any) {
                if (opts.url.includes('/file/')) {
                    return $.Deferred().resolve(file.toJSON());
                }
                return $.Deferred().resolve([file.toJSON()]);
            };
            w.__is(widget.$('.s-select-multifile-button').length, 1, 'multifile button');
            widget.$('.s-select-file-button').click();
            w.__is(arg.parentModel.get('_id'), admin.get('_id'), 'parentModel is admin');
            arg.onItemClick(item);
            arg.parentView._validate();
            await w.__waitFor(() => widget.model && widget.model.value() && widget.model.value().name() === 'e');
            w.__is(widget.model.value().name(), 'e', 'file value name');
            w.__eq(widget.model.get('path'), [], 'file path');

            girder.$.ajax = origAjax;
            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('file default', async ({ page }) => {
        await createUser(page, 'admin');
        await waitForIdlePage(page);
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
            const folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f' });

            const origAjax = girder.$.ajax;
            girder.$.ajax = function (opts: any) {
                if (opts.data && opts.data.public === false) {
                    return $.Deferred().resolve([]);
                }
                return $.Deferred().resolve([folder.toJSON()]);
            };

            const widget = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'file', title: 'Title', id: 'file-widget',
                    extensions: '.png', required: true, channel: 'output',
                }),
                setDefaultOutput: 't',
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            await w.__waitFor(() => widget.model.value() && widget.model.value().name().startsWith('t'));
            w.__match(widget.model.value().name(), /t-Title-.*\.png/, 'default output name');
            w.__is(widget.model.get('parent').name(), 'f', 'default output parent');

            girder.$.ajax = origAjax;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('image', async ({ page }) => {
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
            const file = new girder.models.FileModel({ _id: 'file id', name: 'g' });
            const item = new girder.models.ItemModel({ _id: 'item id', name: 'f', largeImage: { fileId: file.id } });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            let arg: any;
            hProto.initialize = function (_arg: any) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                parentView,
                rootPath: admin,
                el,
                model: new slicer.models.WidgetModel({ type: 'image', title: 'Title', id: 'image-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);

            const origAjax = girder.$.ajax;
            girder.$.ajax = function () {
                return $.Deferred().resolve(file.toJSON());
            };
            w.__is(widget.$('.s-select-multifile-button').length, 1, 'multifile button');
            widget.$('.s-select-file-button').click();
            w.__is(arg.parentModel.get('_id'), admin.get('_id'), 'parentModel is admin');
            arg.onItemClick(item);
            arg.parentView._validate();

            await w.__waitFor(() => widget.model && widget.model.value() && widget.model.value().name() === 'g');
            w.__is(widget.model.value().name(), 'g', 'image value name');
            w.__eq(widget.model.get('path'), [], 'image path');

            girder.$.ajax = origAjax;
            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('check multi exists', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            hProto.initialize = function () {
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                parentView,
                rootPath: admin,
                el,
                model: new slicer.models.WidgetModel({ type: 'item', title: 'Title', id: 'item-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('.s-select-multifile-button').length, 1, 'multifile button');

            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('multiple flag prevents multi', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            hProto.initialize = function () {
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                parentView,
                rootPath: admin,
                el,
                model: new slicer.models.WidgetModel({
                    type: 'item', title: 'Title', id: 'item-widget', multiple: true,
                }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('.s-select-multifile-button').length, 0, 'no multifile button');

            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('multi type swapping', async ({ page }) => {
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const parentView = { registerChildView: () => undefined };
            const el = $('<div/>').appendTo('body').get(0);
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            let arg: any;
            hProto.initialize = function (_arg: any) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () { return this; };

            const widget = new slicer.views.ControlWidget({
                parentView,
                rootPath: admin,
                el,
                model: new slicer.models.WidgetModel({ type: 'item', title: 'Title', id: 'item-widget' }),
            });
            widget.render();
            w.__checkWidgetCommon(widget);
            w.__is(widget.$('.s-select-multifile-button').length, 1, 'multifile button');
            widget.$('.s-select-multifile-button').click();
            w.__is(arg.parentModel.get('_id'), admin.get('_id'), 'parentModel is admin');

            await w.__waitFor(() => $('.modal-footer a.btn-default').length === 1, 8000);
            w.__is(widget.model.get('type'), 'multi', 'type becomes multi');
            w.__is(widget.model.get('defaultType'), 'item', 'defaultType is item');
            $('.modal-footer a.btn-default').click();

            await w.__waitFor(() => $('.modal-dialog:visible').length === 0, 8000);
            widget.$('.s-select-file-button').click();

            await w.__waitFor(() => $('.modal-dialog:visible').length === 1, 8000);
            $('.modal-footer a.btn-default').click();
            w.__is(widget.model.get('type'), 'item', 'type reverts to item');

            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('invalid', async ({ page }) => {
        const fails = await run(page, () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body').get(0);
            const widget = new slicer.views.ControlWidget({
                parentView,
                el,
                model: new slicer.models.WidgetModel({ type: 'invalid', title: 'Title', id: 'invalid-widget' }),
            });
            const origWarn = console.warn;
            let message: string | undefined;
            console.warn = function (m: string) { message = m; };
            widget.render();
            w.__is(message, 'Invalid widget type "invalid"', 'warning message');
            console.warn = origWarn;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });
});

test.describe('Slicer CLI web control widget getRoot', () => {
    setupServer();

    test.beforeEach(async ({ page }) => {
        await page.evaluate(() => {
            const w = window as any;
            w.__fails = [];
            const show = (v: any) => JSON.stringify(v);
            w.__is = (actual: any, expected: any, msg: string) => {
                if (actual !== expected) {
                    w.__fails.push(`${msg}: expected ${show(expected)} got ${show(actual)}`);
                }
            };
            w.__eq = (actual: any, expected: any, msg: string) => {
                if (show(actual) !== show(expected)) {
                    w.__fails.push(`${msg}: expected ${show(expected)} got ${show(actual)}`);
                }
            };
            w.__waitFor = (cond: () => boolean, timeout = 5000) => new Promise<void>((resolve, reject) => {
                const start = Date.now();
                const tick = () => {
                    if (cond()) {
                        resolve();
                        return;
                    }
                    if (Date.now() - start > timeout) {
                        reject(new Error('__waitFor timeout'));
                        return;
                    }
                    setTimeout(tick, 20);
                };
                tick();
            });
        });
    });


    test('getRoot', async ({ page }) => {
        const fails = await page.evaluate(async () => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const $ = girder.$;
            const admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
            const parentView = { registerChildView: () => undefined };

            const hProto = girder.views.widgets.HierarchyWidget.prototype;
            const hInit = hProto.initialize;
            const hRender = hProto.render;
            hProto.initialize = function () { this.breadcrumbs = []; };
            hProto.render = function () { return this; };

            const proto = slicer.views.ControlWidget.prototype;
            const origComplete = proto.completeInitialization;
            const origAjax = girder.$.ajax;

            const item = new girder.models.ItemModel({ _id: 'item id', name: 'd', folderId: 'folder id' });
            const folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin', parentCollection: 'user' });

            const scenario = async (name: string, value: any, expected: any, stub: any) => {
                let settings: any = false;
                proto.completeInitialization = function (s: any) { settings = s; };
                girder.$.ajax = stub;
                const el = $('<div/>').appendTo('body').get(0);
                const widget = new slicer.views.ControlWidget({
                    rootPath: admin,
                    parentView,
                    el,
                    model: new slicer.models.WidgetModel({ type: 'file', title: 'Title', id: 'file-widget', value }),
                });
                widget.render();
                w.__is(widget.$('.s-select-multifile-button').length, 1, `${name}: multifile button`);
                widget.$('.s-select-file-button').click();
                await w.__waitFor(() => settings !== false, 8000);
                w.__is(settings.root ? settings.root.get('_id') : null, expected, `${name}: root id`);
            };

            const okStub = function (opts: any) {
                if (opts.url.includes('/collection/')) { return $.Deferred().resolve(admin.toJSON()); }
                if (opts.url.includes('/item/')) { return $.Deferred().resolve(item.toJSON()); }
                if (opts.url.includes('/folder/')) { return $.Deferred().resolve(folder.toJSON()); }
                return $.Deferred().resolve([item.toJSON()]);
            };

            await scenario(
                'itemId',
                new girder.models.ItemModel({ itemId: 'item id', name: 'd' }),
                folder.get('_id'),
                okStub,
            );
            await scenario(
                'folderId',
                new girder.models.ItemModel({ folderId: 'folder id', name: 'regex' }),
                folder.get('_id'),
                okStub,
            );
            await scenario(
                'parentCollection',
                new girder.models.ItemModel({ parentCollection: 'user', parentId: 'admin' }),
                admin.get('_id'),
                okStub,
            );
            await scenario(
                'itemId error',
                new girder.models.ItemModel({ itemId: 'fake item id', name: 'd' }),
                null,
                function (opts: any) {
                    if (opts.url.includes('/item/')) { return $.Deferred().reject(item.toJSON()); }
                    return okStub(opts);
                },
            );
            await scenario(
                'folderId error',
                new girder.models.ItemModel({ folderId: 'folder id', name: 'd' }),
                null,
                function (opts: any) {
                    if (opts.url.includes('/folder/')) { return $.Deferred().reject(folder.toJSON()); }
                    return okStub(opts);
                },
            );

            proto.completeInitialization = origComplete;
            girder.$.ajax = origAjax;
            hProto.initialize = hInit;
            hProto.render = hRender;
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });
});
