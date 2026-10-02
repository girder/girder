import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';

/**
 * The legacy widget spec exercised Backbone models/collections directly. The
 * plugin namespace is available in the browser, so we run the same model
 * operations there and collect assertion failures.
 */
const evaluateWidgets = async <T>(page: Page, fn: () => T): Promise<T> => page.evaluate(fn);

test.describe('Slicer CLI web widget model', () => {
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
        });
    });

    test('range', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({
                type: 'range',
                title: 'Range widget',
                min: -10,
                max: 10,
                step: 0.5,
            });
            w.__is(model.isNumeric(), true, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');

            model.set('value', '0.5');
            w.__is(model.value(), 0.5, 'value 0.5');
            w.__is(model.isValid(), true, 'valid 0.5');

            model.set('value', 'a number');
            w.__is(model.isValid(), false, 'invalid a number');

            model.set('value', -11);
            w.__is(model.isValid(), false, 'invalid -11');

            model.set('value', 0.75);
            w.__is(model.isValid(), false, 'invalid 0.75');

            model.set('value', 0);
            w.__is(model.isValid(), true, 'valid 0');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('basic number', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'number', title: 'Number widget' });
            w.__is(model.isNumeric(), true, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');

            model.set('value', '0.5');
            w.__is(model.value(), 0.5, 'value 0.5');
            w.__is(model.isValid(), true, 'valid 0.5');

            model.set('value', 'a number');
            w.__is(model.isValid(), false, 'invalid a number');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('integer number', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'number', title: 'Number widget', step: 1 });
            model.set('value', '0.5');
            w.__is(model.value(), 0.5, 'value 0.5');
            w.__is(model.isValid(), false, 'invalid 0.5');
            model.set('value', '-11');
            w.__is(model.isValid(), true, 'valid -11');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('float number', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'number', title: 'Number widget' });
            model.set('value', '1e-10');
            w.__is(model.value(), 1e-10, 'value 1e-10');
            w.__is(model.isValid(), true, 'valid 1e-10');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('boolean', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'boolean', title: 'Boolean widget' });
            w.__is(model.isNumeric(), false, 'isNumeric');
            w.__is(model.isBoolean(), true, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            w.__is(model.value(), false, 'default false');
            w.__is(model.isValid(), true, 'valid default');
            model.set('value', {});
            w.__is(model.value(), true, 'value {}');
            w.__is(model.isValid(), true, 'valid {}');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({
                type: 'string',
                title: 'String widget',
                value: 'Default value',
            });
            w.__is(model.isNumeric(), false, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            w.__is(model.value(), 'Default value', 'default');
            w.__is(model.isValid(), true, 'valid default');
            model.set('value', 1);
            w.__is(model.value(), '1', 'value 1');
            w.__is(model.isValid(), true, 'valid 1');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('color', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'color', title: 'Color widget' });
            w.__is(model.isNumeric(), false, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), true, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            model.set('value', '#ffffff');
            w.__is(model.value(), '#ffffff', 'hex');
            w.__is(model.isValid(), true, 'valid hex');
            model.set('value', 'red');
            w.__is(model.value(), '#ff0000', 'red');
            w.__is(model.isValid(), true, 'valid red');
            model.set('value', 'rgb(0, 255, 0)');
            w.__is(model.value(), '#00ff00', 'rgb');
            w.__is(model.isValid(), true, 'valid rgb');
            model.set('value', [255, 255, 0]);
            w.__is(model.value(), '#ffff00', 'array');
            w.__is(model.isValid(), true, 'valid array');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string-vector', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'string-vector', title: 'String vector widget' });
            w.__is(model.isNumeric(), false, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), true, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            model.set('value', 'a,b,c');
            w.__eq(model.value(), ['a', 'b', 'c'], 'split string');
            w.__is(model.isValid(), true, 'valid split');
            model.set('value', ['a', 1, '2']);
            w.__eq(model.value(), ['a', '1', '2'], 'coerced array');
            w.__is(model.isValid(), true, 'valid coerced');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('number-vector', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({ type: 'number-vector', title: 'Number vector widget' });
            w.__is(model.isNumeric(), true, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), true, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), false, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            model.set('value', 'a,b,c');
            w.__is(model.isValid(), false, 'invalid a,b,c');
            model.set('value', ['a', 1, '2']);
            w.__is(model.isValid(), false, 'invalid mixed');
            model.set('value', '1,2,3');
            w.__eq(model.value(), [1, 2, 3], 'split numbers');
            w.__is(model.isValid(), true, 'valid split');
            model.set('value', ['0', 1, '2']);
            w.__eq(model.value(), [0, 1, 2], 'coerced numbers');
            w.__is(model.isValid(), true, 'valid coerced');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('string-enumeration', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({
                type: 'string-enumeration',
                title: 'String enumeration widget',
                values: ['value 1', 'value 2', 'value 3'],
            });
            w.__is(model.isNumeric(), false, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), true, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            model.set('value', 'value 1');
            w.__is(model.isValid(), true, 'valid value 1');
            model.set('value', 'value 4');
            w.__is(model.isValid(), false, 'invalid value 4');
            model.set('value', 'value 3');
            w.__is(model.isValid(), true, 'valid value 3');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('number-enumeration', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;
            const model = new slicer.models.WidgetModel({
                type: 'number-enumeration',
                title: 'Number enumeration widget',
                values: [11, 12, '13'],
            });
            w.__is(model.isNumeric(), true, 'isNumeric');
            w.__is(model.isBoolean(), false, 'isBoolean');
            w.__is(model.isVector(), false, 'isVector');
            w.__is(model.isColor(), false, 'isColor');
            w.__is(model.isEnumeration(), true, 'isEnumeration');
            w.__is(model.isFile(), false, 'isFile');
            w.__is(model.isItem(), false, 'isItem');
            model.set('value', '11');
            w.__is(model.isValid(), true, 'valid 11');
            model.set('value', 0);
            w.__is(model.isValid(), false, 'invalid 0');
            model.set('value', 13);
            w.__is(model.isValid(), true, 'valid 13');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });

    test('file / item / invalid', async ({ page }) => {
        const fails = await evaluateWidgets(page, () => {
            const w = window as any;
            const slicer = w.girder.plugins.slicer_cli_web;

            const file = new slicer.models.WidgetModel({ type: 'file', title: 'File widget' });
            w.__is(file.isFile(), true, 'file isFile');
            w.__is(file.isItem(), false, 'file isItem');

            const item = new slicer.models.WidgetModel({ type: 'item', title: 'Item widget' });
            w.__is(item.isFile(), false, 'item isFile');
            w.__is(item.isItem(), true, 'item isItem');

            const invalid = new slicer.models.WidgetModel({ type: 'invalid type', title: 'Invalid widget' });
            w.__is(invalid.isNumeric(), false, 'invalid isNumeric');
            w.__is(invalid.isBoolean(), false, 'invalid isBoolean');
            w.__is(invalid.isVector(), false, 'invalid isVector');
            w.__is(invalid.isColor(), false, 'invalid isColor');
            w.__is(invalid.isEnumeration(), false, 'invalid isEnumeration');
            w.__is(invalid.isFile(), false, 'invalid isFile');
            w.__is(invalid.isItem(), false, 'invalid isItem');
            w.__is(invalid.isValid(), false, 'invalid isValid');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });
});

test.describe('Slicer CLI web widget collection', () => {
    setupServer();

    test('values', async ({ page }) => {
        const fails = await page.evaluate(() => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            w.__fails = [];
            w.__eq = (actual: any, expected: any, msg: string) => {
                if (JSON.stringify(actual) !== JSON.stringify(expected)) {
                    w.__fails.push(`${msg}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
                }
            };
            const Backbone = girder.Backbone || w.Backbone;
            const collection = new slicer.collections.WidgetCollection([
                { type: 'range', id: 'range', value: 0 },
                { type: 'number', id: 'number', value: '1' },
                { type: 'boolean', id: 'boolean', value: 'yes' },
                { type: 'string', id: 'string', value: 0 },
                { type: 'color', id: 'color', value: 'red' },
                { type: 'string-vector', id: 'string-vector', value: 'a,b,c' },
                { type: 'number-vector', id: 'number-vector', value: '1,2,3' },
                { type: 'string-enumeration', id: 'string-enumeration', values: ['a'], value: 'a' },
                { type: 'number-enumeration', id: 'number-enumeration', values: [1], value: '1' },
                { type: 'file', id: 'file', value: new Backbone.Model({ id: 'a' }) },
                { type: 'new-file', id: 'new-file', value: new Backbone.Model({ name: 'a', folderId: 'b' }) },
                { type: 'item', id: 'item', value: new Backbone.Model({ id: 'c' }) },
                { type: 'image', id: 'image', value: new Backbone.Model({ id: 'd' }) },
            ]);

            w.__eq(collection.values(), {
                'range': '0',
                'number': '1',
                'boolean': true,
                'string': '0',
                'color': '"#ff0000"',
                'string-vector': '["a","b","c"]',
                'number-vector': '[1,2,3]',
                'string-enumeration': 'a',
                'number-enumeration': '1',
                'file': 'a',
                'new-file_folder': 'b',
                'new-file': 'a',
                'item': 'c',
                'image': 'd',
            }, 'values');
            return w.__fails;
        });
        expect(fails).toEqual([]);
    });
});
