/* globals girderTest, describe, it, waitsFor */

girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var parser;
girderTest.promise.done(function () {
    parser = girder.plugins.slicer_cli_web.parser;
});

describe('XML Schema parser', function () {
    describe('type conversion', function () {
        it('number', function () {
            var type = 'number';
            expect(parser.convert(type, '1')).toBe(1);
        });
        it('string', function () {
            var type = 'string';
            expect(parser.convert(type, '1')).toBe('1');
        });
        it('boolean', function () {
            var type = 'boolean';
            expect(parser.convert(type, 'true')).toBe(true);
            expect(parser.convert(type, 'false')).toBe(false);
            expect(parser.convert(type, '')).toBe(false);
        });
        it('string-vector', function () {
            var type = 'string-vector';
            expect(parser.convert(type, '1,2,3')).toEqual(['1', '2', '3']);
        });
        it('number-vector', function () {
            var type = 'number-vector';
            expect(parser.convert(type, '1,2,3')).toEqual([1, 2, 3]);
        });
        it('number-enumeration', function () {
            var type = 'number-enumeration';
            expect(parser.convert(type, '1')).toEqual(1);
        });
        it('string-enumeration', function () {
            var type = 'string-enumeration';
            expect(parser.convert(type, '1')).toEqual('1');
        });
    });

    describe('constraints', function () {
        it('empty', function () {
            expect(parser.constraints('number'))
                .toEqual({});
        });
        it('missing step', function () {
            var xml = $.parseXML(
                '<constraints><minimum>1</minimum><maximum>3</maximum></constraints>'
            );
            expect(parser.constraints(
                'number',
                xml
            )).toEqual({min: 1, max: 3});
        });
        it('full spec', function () {
            var xml = $.parseXML(
                '<constraints><minimum>0</minimum><maximum>2</maximum><step>0.5</step></constraints>'
            );
            expect(parser.constraints(
                'number',
                xml
            )).toEqual({min: 0, max: 2, step: 0.5});
        });
    });

    describe('parameters', function () {
        it('integer', function () {
            var xml = $.parseXML(
                '<integer>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>An integer</description>' +
                    '</integer>'
            );
            expect(parser.param(
                $(xml).find('integer').get(0)
            )).toEqual({
                type: 'number',
                slicerType: 'integer',
                id: 'foo',
                title: 'arg1',
                channel: 'input',
                description: 'An integer'
            });
        });
        it('string', function () {
            var xml = $.parseXML(
                '<string>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</string>'
            );
            expect(parser.param(
                $(xml).find('string').get(0)
            )).toEqual({
                type: 'string',
                slicerType: 'string',
                id: 'foo',
                title: 'arg1',
                channel: 'input',
                description: 'A description'
            });
        });
        it('boolean', function () {
            var xml = $.parseXML(
                '<boolean>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</boolean>'
            );
            expect(parser.param(
                $(xml).find('boolean').get(0)
            )).toEqual({
                type: 'boolean',
                slicerType: 'boolean',
                id: 'foo',
                channel: 'input',
                title: 'arg1',
                description: 'A description'
            });
        });
        it('double-vector', function () {
            var xml = $.parseXML(
                '<double-vector>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A vector</description>' +
                    '<default>1.5,2.0,2.5</default>' +
                    '</double-vector>'
            );
            expect(parser.param(
                $(xml).find('double-vector').get(0)
            )).toEqual({
                type: 'number-vector',
                slicerType: 'double-vector',
                id: 'foo',
                title: 'arg1',
                channel: 'input',
                description: 'A vector',
                value: [1.5, 2.0, 2.5]
            });
        });
        it('string-vector', function () {
            var xml = $.parseXML(
                '<string-vector>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</string-vector>'
            );
            expect(parser.param(
                $(xml).find('string-vector').get(0)
            )).toEqual({
                type: 'string-vector',
                slicerType: 'string-vector',
                id: 'foo',
                title: 'arg1',
                channel: 'input',
                description: 'A description'
            });
        });
        it('double-enumeration', function () {
            var xml = $.parseXML(
                '<double-enumeration>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A choice</description>' +
                    '<default>1.5</default>' +
                    '<element>1.5</element>' +
                    '<element>2.5</element>' +
                    '<element>3.5</element>' +
                    '</double-enumeration>'
            );
            expect(parser.param(
                $(xml).find('double-enumeration').get(0)
            )).toEqual({
                type: 'number-enumeration',
                slicerType: 'double-enumeration',
                id: 'foo',
                title: 'arg1',
                description: 'A choice',
                channel: 'input',
                value: 1.5,
                values: [1.5, 2.5, 3.5]
            });
        });
        it('string-enumeration', function () {
            var xml = $.parseXML(
                '<string-enumeration>' +
                    '<longflag>foo</longflag>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</string-enumeration>'
            );
            expect(parser.param(
                $(xml).find('string-enumeration').get(0)
            )).toEqual({
                type: 'string-enumeration',
                slicerType: 'string-enumeration',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'input',
                values: []
            });
        });
        it('file', function () {
            var xml = $.parseXML(
                '<file>' +
                    '<longflag>foo</longflag>' +
                    '<channel>input</channel>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</file>'
            );
            expect(parser.param(
                $(xml).find('file').get(0)
            )).toEqual({
                type: 'file',
                slicerType: 'file',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'input',
                multiple: false
            });
        });
        it('directory', function () {
            var xml = $.parseXML(
                '<directory>' +
                    '<longflag>foo</longflag>' +
                    '<channel>input</channel>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</directory>'
            );
            expect(parser.param(
                $(xml).find('directory').get(0)
            )).toEqual({
                type: 'directory',
                slicerType: 'directory',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'input'
            });
        });
        it('image', function () {
            var xml = $.parseXML(
                '<image>' +
                    '<longflag>foo</longflag>' +
                    '<channel>input</channel>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</image>'
            );
            expect(parser.param(
                $(xml).find('image').get(0)
            )).toEqual({
                type: 'image',
                slicerType: 'image',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'input',
                multiple: false
            });
        });
        it('output file', function () {
            var xml = $.parseXML(
                '<file fileExtensions=".txt">' +
                    '<longflag>foo</longflag>' +
                    '<channel>output</channel>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</file>'
            );
            expect(parser.param(
                $(xml).find('file').get(0)
            )).toEqual({
                type: 'new-file',
                slicerType: 'file',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'output',
                extensions: '.txt'
            });

            xml = $.parseXML(
                '<file fileExtensions=".txt">' +
                    '<name>foo</name>' +
                    '<index>0</index>' +
                    '<channel>output</channel>' +
                    '<label>arg1</label>' +
                    '<description>A description</description>' +
                    '</file>'
            );
            expect(parser.param(
                $(xml).find('file').get(0)
            )).toEqual({
                type: 'new-file',
                slicerType: 'file',
                id: 'foo',
                title: 'arg1',
                description: 'A description',
                channel: 'output',
                required: true,
                extensions: '.txt'
            });
        });
        it('ignored output', function () {
            var xml = $.parseXML(
                '<integer>' +
                    '<longflag>foo</longflag>' +
                    '<channel>output</channel>' +
                    '<label>arg1</label>' +
                    '<description>An integer</description>' +
                    '</integer>'
            );
            expect(parser.param(
                $(xml).find('integer').get(0)
            )).toBe(null);
        });
    });

    describe('default value', function () {
        it('no value provided', function () {
            expect(parser.defaultValue('integer', $())).toEqual({});
        });
        it('a integer provided', function () {
            expect(parser.defaultValue(
                'integer',
                $('<default>1</default>')
            )).toEqual({value: '1'});
        });
    });
    xdescribe('parameter groups', function () {
        /**
         * Return a parser with the param component mocked to
         * limit testing here to just the parameter groups.
         */
        function mockParser() {
            function parseParam(x) {
                return x.tagName;
            }
            return _.extend({}, parser, {
                _parseParam: parseParam
            });
        }

        it('a single group', function () {
            var xml = $.parseXML(
                '<parameters>' +
                    '<label>group1</label>' +
                    '<description>This is group1</description>' +
                    '<param1></param1>' +
                    '<param2></param2>' +
                    '<param3></param3>' +
                    '</parameters>'
            );
            expect(
                mockParser()._parseGroup($(xml).find('label').get(0))
            ).toEqual({
                label: 'group1',
                description: 'This is group1',
                parameters: ['param1', 'param2', 'param3']
            });
        });

        it('multiple groups', function () {
            var xml = $.parseXML(
                '<parameters>' +
                    '<label>group1</label>' +
                    '<description>This is group1</description>' +
                    '<param1></param1>' +
                    '<label>group2</label>' +
                    '<description>This is group2</description>' +
                    '<param2></param2>' +
                    '</parameters>'
            );
            expect(
                mockParser()._parseGroup($(xml).find('label').get(0))
            ).toEqual({
                label: 'group1',
                description: 'This is group1',
                parameters: ['param1']
            });
            expect(
                mockParser()._parseGroup($(xml).find('label').get(1))
            ).toEqual({
                label: 'group2',
                description: 'This is group2',
                parameters: ['param2']
            });
        });
    });

    describe('Panels', function () {
        it('default panel with one param group', function () {
            var xml = $.parseXML(
                '<parameters>' +
                    '<label>group1</label>' +
                    '<description>This is group1</description>' +
                    '<integer></integer>' +
                    '</parameters>'
            );
            expect(
                parser.panel($(xml).find('parameters').get(0)).advanced
            ).toBe(false);
        });

        it('advanced panel with one param group', function () {
            var xml = $.parseXML(
                '<parameters advanced="true">' +
                    '<label>group1</label>' +
                    '<description>This is group1</description>' +
                    '<integer></integer>' +
                    '</parameters>'
            );
            expect(
                parser.panel($(xml).find('parameters').get(0)).advanced
            ).toBe(true);
        });

        it('a panel with multiple param groups', function () {
            var xml = $.parseXML(
                '<parameters advanced="false">' +
                    '<label>group1</label>' +
                    '<description>This is group1</description>' +
                    '<integer></integer>' +
                    '<label>group2</label>' +
                    '<description>This is group2</description>' +
                    '<integer></integer>' +
                    '<label>group3</label>' +
                    '<description>This is group3</description>' +
                    '<integer></integer>' +
                    '</parameters>'
            );
            var parsed = parser.panel($(xml).find('parameters').get(0));
            expect(
                parsed.advanced
            ).toBe(false);
            expect(
                parsed.groups.length
            ).toBe(3);
        });
    });

    describe('Executable', function () {
        it('a minimal executable', function () {
            var xml = $.parseXML(
                '<executable>' +
                    '<title>The title</title>' +
                    '<description>A description</description>' +
                    '</executable>'
            );
            expect(
                parser.parse(xml)
            ).toEqual({
                title: 'The title',
                description: 'A description',
                panels: []
            });
        });

        it('optional metadata', function () {
            var xml = $.parseXML(
                '<executable>' +
                    '<title>The title</title>' +
                    '<description>A description</description>' +
                    '<version>0.0.0</version>' +
                    '<documentation-url>//a.url.com</documentation-url>' +
                    '<license>WTFPL</license>' +
                    '<contributor>John Doe</contributor>' +
                    '<acknowledgements>Jane Doe</acknowledgements>' +
                    '</executable>'
            );
            expect(
                parser.parse(xml)
            ).toEqual({
                title: 'The title',
                description: 'A description',
                version: '0.0.0',
                'documentation-url': '//a.url.com',
                license: 'WTFPL',
                contributor: 'John Doe',
                acknowledgements: 'Jane Doe',
                panels: []
            });
        });

        it('a single parameter panel', function () {
            var xml = $.parseXML(
                '<executable>' +
                    '<title>The title</title>' +
                    '<description>A description</description>' +
                    '<parameters>params1</parameters>' +
                    '</executable>'
            );
            var parsed = parser.parse(xml);
            expect(
                parsed
            ).toEqual({
                title: 'The title',
                description: 'A description',
                panels: []
            });
        });
    });

    // integration test with no mocking
    it('a full example spec', function () {
        var spec = [
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
            '</executable>'
        ].join('');

        var opts = {};
        expect(
            parser.parse(spec, opts)
        ).toEqual(
            {
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
                                        'value': 30
                                    }
                                ]
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
                                        'step': 0
                                    }
                                ]
                            }
                        ]
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
                                        'value': [
                                            1.3,
                                            2,
                                            -14
                                        ]
                                    },
                                    {
                                        'type': 'string-vector',
                                        'slicerType': 'string-vector',
                                        'id': 'stringVector',
                                        'title': 'String Vector Parameter',
                                        'description': 'A vector of strings',
                                        'channel': 'input',
                                        'value': [
                                            '"foo"',
                                            'bar',
                                            '"foobar"'
                                        ]
                                    }
                                ]
                            }
                        ]
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
                                        'values': [
                                            'foo',
                                            '"foobar"',
                                            'foofoo'
                                        ],
                                        'value': 'foo'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        );
        expect(opts.output).toBe(true);
    });
});
