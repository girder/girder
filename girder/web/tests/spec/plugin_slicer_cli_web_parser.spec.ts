import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';

/**
 * Helpers that run the slicer_cli_web parser inside the browser, where the
 * plugin namespace (window.girder.plugins.slicer_cli_web.parser) is available.
 */
async function convert(page: Page, type: string, value: string) {
    return page.evaluate(({ type, value }) => {
        const girder = (window as any).girder;
        return girder.plugins.slicer_cli_web.parser.convert(type, value);
    }, { type, value });
}

async function constraints(page: Page, type: string, xml?: string) {
    return page.evaluate(({ type, xml }) => {
        const girder = (window as any).girder;
        const $ = girder.$;
        const tag = xml === undefined ? undefined : $.parseXML(xml);
        return girder.plugins.slicer_cli_web.parser.constraints(type, tag);
    }, { type, xml });
}

async function param(page: Page, xml: string, selector: string) {
    return page.evaluate(({ xml, selector }) => {
        const girder = (window as any).girder;
        const $ = girder.$;
        const tag = $($.parseXML(xml)).find(selector).get(0);
        return girder.plugins.slicer_cli_web.parser.param(tag);
    }, { xml, selector });
}

async function defaultValue(page: Page, type: string, xml: string | null) {
    return page.evaluate(({ type, xml }) => {
        const girder = (window as any).girder;
        const $ = girder.$;
        const value = xml === null ? $() : $(xml);
        return girder.plugins.slicer_cli_web.parser.defaultValue(type, value);
    }, { type, xml });
}

async function panel(page: Page, xml: string) {
    return page.evaluate(({ xml }) => {
        const girder = (window as any).girder;
        const $ = girder.$;
        const tag = $($.parseXML(xml)).find('parameters').get(0);
        return girder.plugins.slicer_cli_web.parser.panel(tag);
    }, { xml });
}

async function parse(page: Page, spec: string) {
    return page.evaluate(({ spec }) => {
        const girder = (window as any).girder;
        const opts = {};
        const gui = girder.plugins.slicer_cli_web.parser.parse(spec, opts);
        return { gui, opts };
    }, { spec });
}

test.describe('Slicer CLI web XML schema parser', () => {
    setupServer();

    test('type conversion', async ({ page }) => {
        expect(await convert(page, 'number', '1')).toBe(1);
        expect(await convert(page, 'string', '1')).toBe('1');
        expect(await convert(page, 'boolean', 'true')).toBe(true);
        expect(await convert(page, 'boolean', 'false')).toBe(false);
        expect(await convert(page, 'boolean', '')).toBe(false);
        expect(await convert(page, 'string-vector', '1,2,3')).toEqual(['1', '2', '3']);
        expect(await convert(page, 'number-vector', '1,2,3')).toEqual([1, 2, 3]);
        expect(await convert(page, 'number-enumeration', '1')).toEqual(1);
        expect(await convert(page, 'string-enumeration', '1')).toEqual('1');
    });

    test('constraints', async ({ page }) => {
        expect(await constraints(page, 'number')).toEqual({});
        expect(await constraints(
            page,
            'number',
            '<constraints><minimum>1</minimum><maximum>3</maximum></constraints>',
        )).toEqual({ min: 1, max: 3 });
        expect(await constraints(
            page,
            'number',
            '<constraints><minimum>0</minimum><maximum>2</maximum><step>0.5</step></constraints>',
        )).toEqual({ min: 0, max: 2, step: 0.5 });
    });

    test('parameters', async ({ page }) => {
        expect(await param(
            page,
            '<integer><longflag>foo</longflag><label>arg1</label>' +
                '<description>An integer</description></integer>',
            'integer',
        )).toEqual({
            type: 'number',
            slicerType: 'integer',
            id: 'foo',
            title: 'arg1',
            channel: 'input',
            description: 'An integer',
        });

        expect(await param(
            page,
            '<string><longflag>foo</longflag><label>arg1</label>' +
                '<description>A description</description></string>',
            'string',
        )).toEqual({
            type: 'string',
            slicerType: 'string',
            id: 'foo',
            title: 'arg1',
            channel: 'input',
            description: 'A description',
        });

        expect(await param(
            page,
            '<boolean><longflag>foo</longflag><label>arg1</label>' +
                '<description>A description</description></boolean>',
            'boolean',
        )).toEqual({
            type: 'boolean',
            slicerType: 'boolean',
            id: 'foo',
            channel: 'input',
            title: 'arg1',
            description: 'A description',
        });

        expect(await param(
            page,
            '<double-vector><longflag>foo</longflag><label>arg1</label>' +
                '<description>A vector</description>' +
                '<default>1.5,2.0,2.5</default></double-vector>',
            'double-vector',
        )).toEqual({
            type: 'number-vector',
            slicerType: 'double-vector',
            id: 'foo',
            title: 'arg1',
            channel: 'input',
            description: 'A vector',
            value: [1.5, 2.0, 2.5],
        });

        expect(await param(
            page,
            '<string-vector><longflag>foo</longflag><label>arg1</label>' +
                '<description>A description</description></string-vector>',
            'string-vector',
        )).toEqual({
            type: 'string-vector',
            slicerType: 'string-vector',
            id: 'foo',
            title: 'arg1',
            channel: 'input',
            description: 'A description',
        });

        expect(await param(
            page,
            '<double-enumeration><longflag>foo</longflag><label>arg1</label>' +
                '<description>A choice</description><default>1.5</default>' +
                '<element>1.5</element><element>2.5</element>' +
                '<element>3.5</element></double-enumeration>',
            'double-enumeration',
        )).toEqual({
            type: 'number-enumeration',
            slicerType: 'double-enumeration',
            id: 'foo',
            title: 'arg1',
            description: 'A choice',
            channel: 'input',
            value: 1.5,
            values: [1.5, 2.5, 3.5],
        });

        expect(await param(
            page,
            '<string-enumeration><longflag>foo</longflag><label>arg1</label>' +
                '<description>A description</description></string-enumeration>',
            'string-enumeration',
        )).toEqual({
            type: 'string-enumeration',
            slicerType: 'string-enumeration',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'input',
            values: [],
        });

        expect(await param(
            page,
            '<file><longflag>foo</longflag><channel>input</channel><label>arg1</label>' +
                '<description>A description</description></file>',
            'file',
        )).toEqual({
            type: 'file',
            slicerType: 'file',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'input',
            multiple: false,
        });

        expect(await param(
            page,
            '<directory><longflag>foo</longflag><channel>input</channel><label>arg1</label>' +
                '<description>A description</description></directory>',
            'directory',
        )).toEqual({
            type: 'directory',
            slicerType: 'directory',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'input',
        });

        expect(await param(
            page,
            '<image><longflag>foo</longflag><channel>input</channel><label>arg1</label>' +
                '<description>A description</description></image>',
            'image',
        )).toEqual({
            type: 'image',
            slicerType: 'image',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'input',
            multiple: false,
        });

        expect(await param(
            page,
            '<file fileExtensions=".txt"><longflag>foo</longflag><channel>output</channel>' +
                '<label>arg1</label><description>A description</description></file>',
            'file',
        )).toEqual({
            type: 'new-file',
            slicerType: 'file',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'output',
            extensions: '.txt',
        });

        expect(await param(
            page,
            '<file fileExtensions=".txt"><name>foo</name><index>0</index>' +
                '<channel>output</channel><label>arg1</label>' +
                '<description>A description</description></file>',
            'file',
        )).toEqual({
            type: 'new-file',
            slicerType: 'file',
            id: 'foo',
            title: 'arg1',
            description: 'A description',
            channel: 'output',
            required: true,
            extensions: '.txt',
        });

        expect(await param(
            page,
            '<integer><longflag>foo</longflag><channel>output</channel><label>arg1</label>' +
                '<description>An integer</description></integer>',
            'integer',
        )).toBe(null);
    });

    test('default value', async ({ page }) => {
        expect(await defaultValue(page, 'integer', null)).toEqual({});
        expect(await defaultValue(page, 'integer', '<default>1</default>')).toEqual({ value: '1' });
    });

    test('panels', async ({ page }) => {
        expect((await panel(
            page,
            '<parameters><label>group1</label><description>This is group1</description>' +
                '<integer></integer></parameters>',
        )).advanced).toBe(false);

        expect((await panel(
            page,
            '<parameters advanced="true"><label>group1</label>' +
                '<description>This is group1</description><integer></integer></parameters>',
        )).advanced).toBe(true);

        const parsed = await panel(
            page,
            '<parameters advanced="false"><label>group1</label>' +
                '<description>This is group1</description><integer></integer>' +
                '<label>group2</label><description>This is group2</description>' +
                '<integer></integer><label>group3</label>' +
                '<description>This is group3</description><integer></integer></parameters>',
        );
        expect(parsed.advanced).toBe(false);
        expect(parsed.groups.length).toBe(3);
    });

    test('executable', async ({ page }) => {
        expect((await parse(
            page,
            '<executable><title>The title</title><description>A description</description></executable>',
        )).gui).toEqual({
            title: 'The title',
            description: 'A description',
            panels: [],
        });

        expect((await parse(
            page,
            '<executable><title>The title</title><description>A description</description>' +
                '<version>0.0.0</version><documentation-url>//a.url.com</documentation-url>' +
                '<license>WTFPL</license><contributor>John Doe</contributor>' +
                '<acknowledgements>Jane Doe</acknowledgements></executable>',
        )).gui).toEqual({
            title: 'The title',
            description: 'A description',
            version: '0.0.0',
            'documentation-url': '//a.url.com',
            license: 'WTFPL',
            contributor: 'John Doe',
            acknowledgements: 'Jane Doe',
            panels: [],
        });

        expect((await parse(
            page,
            '<executable><title>The title</title><description>A description</description>' +
                '<parameters>params1</parameters></executable>',
        )).gui).toEqual({
            title: 'The title',
            description: 'A description',
            panels: [],
        });
    });

    test('a full example spec', async ({ page }) => {
        const spec = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<executable>',
            '<category>Tours</category>',
            '<title>Execution Model Tour</title>',
            '<description>',
            'Shows one of each type of parameter.',
            '</description>',
            '<version>1.0</version>',
            '<documentation-url></documentation-url>',
            '<license></license>',
            '<contributor>Daniel Blezek</contributor>',
            '<parameters>',
            '<label>Scalar Parameters</label>',
            '<description>',
            'Variations on scalar parameters',
            '</description>',
            '<integer>',
            '<name>integerVariable</name>',
            '<flag>i</flag>',
            '<longflag>integer</longflag>',
            '<description>',
            'An integer without constraints',
            '</description>',
            '<label>Integer Parameter</label>',
            '<default>30</default>',
            '</integer>',
            '<label>Scalar Parameters With Constraints</label>',
            '<description>Variations on scalar parameters</description>',
            '<double>',
            '<name>doubleVariable</name>',
            '<flag>d</flag>',
            '<longflag>double</longflag>',
            '<description>An double with constraints</description>',
            '<label>Double Parameter</label>',
            '<default>30</default>',
            '<constraints>',
            '<minimum>0</minimum>',
            '<maximum>1.e3</maximum>',
            '<step>0</step>',
            '</constraints>',
            '</double>',
            '<double>',
            '<label>Output parameter that should be ignored</label>',
            '<name>outputVariable</name>',
            '<flag>o</flag>',
            '<longflag>double-output</longflag>',
            '<channel>output</channel>',
            '</double>',
            '</parameters>',
            '<parameters>',
            '<label>Vector Parameters</label>',
            '<description>Variations on vector parameters</description>',
            '<float-vector>',
            '<name>floatVector</name>',
            '<flag>f</flag>',
            '<description>A vector of floats</description>',
            '<label>Float Vector Parameter</label>',
            '<default>1.3,2,-14</default>',
            '</float-vector>',
            '<string-vector>',
            '<name>stringVector</name>',
            '<longflag>string_vector</longflag>',
            '<description>A vector of strings</description>',
            '<label>String Vector Parameter</label>',
            '<default>"foo",bar,"foobar"</default>',
            '</string-vector>',
            '</parameters>',
            '<parameters>',
            '<label>Enumeration Parameters</label>',
            '<description>Variations on enumeration parameters</description>',
            '<string-enumeration>',
            '<name>stringChoice</name>',
            '<flag>e</flag>',
            '<longflag>enumeration</longflag>',
            '<description>An enumeration of strings</description>',
            '<label>String Enumeration Parameter</label>',
            '<default>foo</default>',
            '<element>foo</element>',
            '<element>"foobar"</element>',
            '<element>foofoo</element>',
            '</string-enumeration>',
            '</parameters>',
            '<parameters>',
            '</parameters>',
            '</executable>',
        ].join('');

        const { gui, opts } = await parse(page, spec);
        expect(gui).toEqual({
            'title': 'Execution Model Tour',
            'description': 'Shows one of each type of parameter.',
            'version': '1.0',
            'documentation-url': '',
            'license': '',
            'contributor': 'Daniel Blezek',
            'panels': [
                {
                    'advanced': false,
                    'groups': [
                        {
                            'label': 'Scalar Parameters',
                            'description': 'Variations on scalar parameters',
                            'parameters': [
                                {
                                    'type': 'number',
                                    'slicerType': 'integer',
                                    'id': 'integerVariable',
                                    'title': 'Integer Parameter',
                                    'description': 'An integer without constraints',
                                    'channel': 'input',
                                    'value': 30,
                                },
                            ],
                        },
                        {
                            'label': 'Scalar Parameters With Constraints',
                            'description': 'Variations on scalar parameters',
                            'parameters': [
                                {
                                    'type': 'number',
                                    'slicerType': 'double',
                                    'id': 'doubleVariable',
                                    'title': 'Double Parameter',
                                    'description': 'An double with constraints',
                                    'channel': 'input',
                                    'value': 30,
                                    'min': 0,
                                    'max': 1000,
                                    'step': 0,
                                },
                            ],
                        },
                    ],
                },
                {
                    'advanced': false,
                    'groups': [
                        {
                            'label': 'Vector Parameters',
                            'description': 'Variations on vector parameters',
                            'parameters': [
                                {
                                    'type': 'number-vector',
                                    'slicerType': 'float-vector',
                                    'id': 'floatVector',
                                    'title': 'Float Vector Parameter',
                                    'description': 'A vector of floats',
                                    'channel': 'input',
                                    'value': [1.3, 2, -14],
                                },
                                {
                                    'type': 'string-vector',
                                    'slicerType': 'string-vector',
                                    'id': 'stringVector',
                                    'title': 'String Vector Parameter',
                                    'description': 'A vector of strings',
                                    'channel': 'input',
                                    'value': ['"foo"', 'bar', '"foobar"'],
                                },
                            ],
                        },
                    ],
                },
                {
                    'advanced': false,
                    'groups': [
                        {
                            'label': 'Enumeration Parameters',
                            'description': 'Variations on enumeration parameters',
                            'parameters': [
                                {
                                    'type': 'string-enumeration',
                                    'slicerType': 'string-enumeration',
                                    'id': 'stringChoice',
                                    'title': 'String Enumeration Parameter',
                                    'description': 'An enumeration of strings',
                                    'channel': 'input',
                                    'values': ['foo', '"foobar"', 'foofoo'],
                                    'value': 'foo',
                                },
                            ],
                        },
                    ],
                },
            ],
        });
        expect(opts.output).toBe(true);
    });
});
