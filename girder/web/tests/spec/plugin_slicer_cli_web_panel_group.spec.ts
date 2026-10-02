import { expect, test } from '@playwright/test';

import { setupServer } from '../server';

const SPEC_XML = '' +
    '<?xml version="1.0" encoding="UTF-8" ?>' +
    '<executable>' +
    '  <category>Example</category>' +
    '  <title>Simple Example</title>' +
    '  <description>Report on a few input parameters.</description>' +
    '  <version>0.1.0</version>' +
    '  <license>Apache 2.0</license>' +
    '  <contributor>David Manthey (Kitware)</contributor>' +
    '  <parameters>' +
    '    <label>IO</label>' +
    '    <description>Input/output parameters.</description>' +
    '    <image>' +
    '      <name>ImageFile</name>' +
    '      <label>Input Image</label>' +
    '      <channel>input</channel>' +
    '      <description>Input image</description>' +
    '      <index>0</index>' +
    '    </image>' +
    '    <double-vector>' +
    '      <name>Color1</name>' +
    '      <label>RGB Color</label>' +
    '      <description>An RGB Color Vector</description>' +
    '      <channel>input</channel>' +
    '      <index>1</index>' +
    '    </double-vector>' +
    '    <double-vector>' +
    '      <name>Color2</name>' +
    '      <label>YCbCr Color</label>' +
    '      <description>A YCBCr Color Vector</description>' +
    '      <channel>input</channel>' +
    '      <index>2</index>' +
    '    </double-vector>' +
    '  </parameters>' +
    '</executable>';

test.describe('Slicer CLI web panel group', () => {
    setupServer();

    test('panel group', async ({ page }) => {
        const fails = await page.evaluate(async (xml) => {
            const w = window as any;
            const girder = w.girder;
            const slicer = girder.plugins.slicer_cli_web;
            const parentView = { registerChildView: () => undefined };
            const el = girder.$('<div/>').appendTo('body');

            const failures: string[] = [];
            const is = (actual: any, expected: any, msg: string) => {
                if (actual !== expected) {
                    failures.push(`${msg}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
                }
            };
            const waitFor = (cond: () => boolean, timeout = 5000) => new Promise<void>((resolve, reject) => {
                const start = Date.now();
                const tick = () => {
                    if (cond()) {
                        resolve();
                        return;
                    }
                    if (Date.now() - start > timeout) {
                        reject(new Error('waitFor timeout'));
                        return;
                    }
                    setTimeout(tick, 20);
                };
                tick();
            });

            const view = new slicer.views.PanelGroup({
                closeButton: true,
                parentView,
                el: el.get(0),
            });
            view.render();
            is(view.$el.hasClass('hidden'), true, 'hidden initially');

            view.setAnalysis('/test', xml);
            await waitFor(() => view.panels.length > 0);
            is(view.panels.length, 1, 'panel count');
            return failures;
        }, SPEC_XML);
        expect(fails).toEqual([]);
    });
});
