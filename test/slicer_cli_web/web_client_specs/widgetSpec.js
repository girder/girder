girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();

describe('setup', function () {
    it('login', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'password')();
    });
});

describe('widget model', function () {
    // test different widget types
    it('range', function () {
        var w = new slicer.models.WidgetModel({
            type: 'range',
            title: 'Range widget',
            min: -10,
            max: 10,
            step: 0.5
        });
        expect(w.isNumeric()).toBe(true);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', '0.5');
        expect(w.value()).toBe(0.5);
        expect(w.isValid()).toBe(true);

        w.set('value', 'a number');
        expect(w.isValid()).toBe(false);

        w.set('value', -11);
        expect(w.isValid()).toBe(false);

        w.set('value', 0.75);
        expect(w.isValid()).toBe(false);

        w.set('value', 0);
        expect(w.isValid()).toBe(true);
    });
    it('basic number', function () {
        var w = new slicer.models.WidgetModel({
            type: 'number',
            title: 'Number widget'
        });
        expect(w.isNumeric()).toBe(true);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', '0.5');
        expect(w.value()).toBe(0.5);
        expect(w.isValid()).toBe(true);

        w.set('value', 'a number');
        expect(w.isValid()).toBe(false);
    });
    it('integer number', function () {
        var w = new slicer.models.WidgetModel({
            type: 'number',
            title: 'Number widget',
            step: 1
        });
        w.set('value', '0.5');
        expect(w.value()).toBe(0.5);
        expect(w.isValid()).toBe(false);

        w.set('value', '-11');
        expect(w.isValid()).toBe(true);
    });
    it('float number', function () {
        var w = new slicer.models.WidgetModel({
            type: 'number',
            title: 'Number widget'
        });
        w.set('value', '1e-10');
        expect(w.value()).toBe(1e-10);
        expect(w.isValid()).toBe(true);
    });
    it('boolean', function () {
        var w = new slicer.models.WidgetModel({
            type: 'boolean',
            title: 'Boolean widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(true);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        expect(w.value()).toBe(false);
        expect(w.isValid()).toBe(true);

        w.set('value', {});
        expect(w.value()).toBe(true);
        expect(w.isValid()).toBe(true);
    });
    it('string', function () {
        var w = new slicer.models.WidgetModel({
            type: 'string',
            title: 'String widget',
            value: 'Default value'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        expect(w.value()).toBe('Default value');
        expect(w.isValid()).toBe(true);

        w.set('value', 1);
        expect(w.value()).toBe('1');
        expect(w.isValid()).toBe(true);
    });
    it('color', function () {
        var w = new slicer.models.WidgetModel({
            type: 'color',
            title: 'Color widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(true);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', '#ffffff');
        expect(w.value()).toBe('#ffffff');
        expect(w.isValid()).toBe(true);

        w.set('value', 'red');
        expect(w.value()).toBe('#ff0000');
        expect(w.isValid()).toBe(true);

        w.set('value', 'rgb(0, 255, 0)');
        expect(w.value()).toBe('#00ff00');
        expect(w.isValid()).toBe(true);

        w.set('value', [255, 255, 0]);
        expect(w.value()).toBe('#ffff00');
        expect(w.isValid()).toBe(true);
    });
    it('string-vector', function () {
        var w = new slicer.models.WidgetModel({
            type: 'string-vector',
            title: 'String vector widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(true);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', 'a,b,c');
        expect(w.value()).toEqual(['a', 'b', 'c']);
        expect(w.isValid()).toBe(true);

        w.set('value', ['a', 1, '2']);
        expect(w.value()).toEqual(['a', '1', '2']);
        expect(w.isValid()).toBe(true);
    });
    it('number-vector', function () {
        var w = new slicer.models.WidgetModel({
            type: 'number-vector',
            title: 'Number vector widget'
        });
        expect(w.isNumeric()).toBe(true);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(true);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', 'a,b,c');
        expect(w.isValid()).toBe(false);

        w.set('value', ['a', 1, '2']);
        expect(w.isValid()).toBe(false);

        w.set('value', '1,2,3');
        expect(w.value()).toEqual([1, 2, 3]);
        expect(w.isValid()).toBe(true);

        w.set('value', ['0', 1, '2']);
        expect(w.value()).toEqual([0, 1, 2]);
        expect(w.isValid()).toBe(true);
    });
    it('string-enumeration', function () {
        var w = new slicer.models.WidgetModel({
            type: 'string-enumeration',
            title: 'String enumeration widget',
            values: [
                'value 1',
                'value 2',
                'value 3'
            ]
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(true);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', 'value 1');
        expect(w.isValid()).toBe(true);

        w.set('value', 'value 4');
        expect(w.isValid()).toBe(false);

        w.set('value', 'value 3');
        expect(w.isValid()).toBe(true);
    });
    it('number-enumeration', function () {
        var w = new slicer.models.WidgetModel({
            type: 'number-enumeration',
            title: 'Number enumeration widget',
            values: [
                11,
                12,
                '13'
            ]
        });
        expect(w.isNumeric()).toBe(true);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(true);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        w.set('value', '11');
        expect(w.isValid()).toBe(true);

        w.set('value', 0);
        expect(w.isValid()).toBe(false);

        w.set('value', 13);
        expect(w.isValid()).toBe(true);
    });
    it('file', function () {
        var w = new slicer.models.WidgetModel({
            type: 'file',
            title: 'File widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(true);
        expect(w.isItem()).toBe(false);
    });
    it('item', function () {
        var w = new slicer.models.WidgetModel({
            type: 'item',
            title: 'Item widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(true);
    });
    it('invalid', function () {
        var w = new slicer.models.WidgetModel({
            type: 'invalid type',
            title: 'Invalid widget'
        });
        expect(w.isNumeric()).toBe(false);
        expect(w.isBoolean()).toBe(false);
        expect(w.isVector()).toBe(false);
        expect(w.isColor()).toBe(false);
        expect(w.isEnumeration()).toBe(false);
        expect(w.isFile()).toBe(false);
        expect(w.isItem()).toBe(false);

        expect(w.isValid()).toBe(false);
    });
});

describe('widget collection', function () {
    it('values', function () {
        var c = new slicer.collections.WidgetCollection([
            {type: 'range', id: 'range', value: 0},
            {type: 'number', id: 'number', value: '1'},
            {type: 'boolean', id: 'boolean', value: 'yes'},
            {type: 'string', id: 'string', value: 0},
            {type: 'color', id: 'color', value: 'red'},
            {type: 'string-vector', id: 'string-vector', value: 'a,b,c'},
            {type: 'number-vector', id: 'number-vector', value: '1,2,3'},
            {type: 'string-enumeration', id: 'string-enumeration', values: ['a'], value: 'a'},
            {type: 'number-enumeration', id: 'number-enumeration', values: [1], value: '1'},
            {type: 'file', id: 'file', value: new Backbone.Model({id: 'a'})},
            {type: 'new-file', id: 'new-file', value: new Backbone.Model({name: 'a', folderId: 'b'})},
            {type: 'item', id: 'item', value: new Backbone.Model({id: 'c'})},
            {type: 'image', id: 'image', value: new Backbone.Model({id: 'd'})}
        ]);

        expect(c.values()).toEqual({
            range: '0',
            number: '1',
            boolean: true,
            string: '0',
            color: '"#ff0000"',
            'string-vector': '["a","b","c"]',
            'number-vector': '[1,2,3]',
            'string-enumeration': 'a',
            'number-enumeration': '1',
            'file': 'a',
            'new-file_folder': 'b',
            'new-file': 'a',
            'item': 'c',
            'image': 'd'
        });
    });
});

describe('control widget view', function () {
    var $el, admin, hInit, hRender, hProto, parentView = {
        registerChildView: function () { }
    };

    function checkWidgetCommon(widget) {
        var model = widget.model;
        expect(widget.$('label[for="' + model.id + '"]').text())
            .toBe(model.get('title'));
        if (widget.model.isEnumeration()) {
            expect(widget.$('select#' + model.id).length).toBe(1);
        } else {
            expect(widget.$('input#' + model.id).length).toBe(1);
        }
    }

    beforeEach(function () {
        admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
        hProto = girder.views.widgets.HierarchyWidget.prototype;
        hInit = hProto.initialize;
        hRender = hProto.render;

        $el = $('<div/>').appendTo('body');
    });

    afterEach(function () {
        hProto.initialize = hInit;
        hProto.render = hRender;
        $el.remove();
    });

    it('range', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'range',
                title: 'Title',
                id: 'range-widget',
                value: 2,
                min: 0,
                max: 10,
                step: 2
            })
        });

        w.render();

        checkWidgetCommon(w);
        expect(w.$('input').val()).toBe('2');
        w.$('input').val('4').trigger('change');
        expect(w.model.value()).toBe(4);
    });

    it('number', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'number',
                title: 'Title',
                id: 'number-widget',
                value: 2,
                min: 0,
                max: 10,
                step: 2
            })
        });

        w.render();

        checkWidgetCommon(w);
        expect(w.$('input').val()).toBe('2');
        w.$('input').val('4').trigger('change');
        expect(w.model.value()).toBe(4);

        w.$('input').val('4').trigger('change');
        expect(w.$('.form-group').hasClass('has-error')).toBe(false);

        w.remove();
    });

    it('boolean', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'boolean',
                title: 'Title',
                id: 'boolean-widget'
            })
        });

        w.render();

        checkWidgetCommon(w);
        expect(w.$('input').prop('checked')).toBe(false);

        w.$('input').click();
        expect(w.model.value()).toBe(true);

        w.remove();
    });

    it('string', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'string',
                title: 'Title',
                id: 'string-widget',
                value: 'default'
            })
        });

        w.render();

        checkWidgetCommon(w);
        expect(w.$('input').val()).toBe('default');

        w.$('input').val('new value').trigger('change');
        expect(w.model.value()).toBe('new value');

        w.remove();
    });

    it('color', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'color',
                title: 'Title',
                id: 'color-widget',
                value: 'red'
            })
        });

        w.render();

        checkWidgetCommon(w);
        expect(w.model.value()).toBe('#ff0000');

        w.$('.input-group-addon').click();
        expect($('.colorpicker-visible').length).toBe(1);

        w.$('input').val('#ffffff').trigger('change');
        expect(w.model.value()).toBe('#ffffff');

        w.remove();
    });

    it('string-vector', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'string-vector',
                title: 'Title',
                id: 'string-vector-widget',
                value: 'one,two,three'
            })
        });

        w.render();
        checkWidgetCommon(w);
        expect(w.$('input').val()).toBe('one,two,three');

        w.$('input').val('1,2,3').trigger('change');
        expect(w.model.value()).toEqual(['1', '2', '3']);

        w.remove();
    });

    it('number-vector', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'number-vector',
                title: 'Title',
                id: 'number-vector-widget',
                value: '1,2,3'
            })
        });

        w.render();
        checkWidgetCommon(w);
        expect(w.$('input').val()).toBe('1,2,3');

        w.$('input').val('10,20,30').trigger('change');
        expect(w.model.value()).toEqual([10, 20, 30]);

        w.remove();
    });

    it('string-enumeration', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'string-enumeration',
                title: 'Title',
                id: 'string-enumeration-widget',
                value: 'value 2',
                values: [
                    'value 1',
                    'value 2',
                    'value 3'
                ]
            })
        });

        w.render();
        checkWidgetCommon(w);
        expect(w.$('select').val()).toBe('value 2');

        w.$('select').val('value 3').trigger('change');
        expect(w.model.value()).toBe('value 3');

        w.remove();
    });

    it('number-enumeration', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'number-enumeration',
                title: 'Title',
                id: 'number-enumeration-widget',
                value: 200,
                values: [
                    100,
                    200,
                    300
                ]
            })
        });

        w.render();
        checkWidgetCommon(w);
        expect(w.$('select').val()).toBe('200');

        w.$('select').val('300').trigger('change');
        expect(w.model.value()).toBe(300);

        w.remove();
    });

    it('item', function () {
        var arg, item, w;
        runs(function () {
            item = new girder.models.ItemModel({id: 'model id', name: 'b'});

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};

            w = new slicer.views.ControlWidget({
                parentView: parentView,
                rootPath: admin,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'item',
                    title: 'Title',
                    id: 'item-widget'
                })
            });

            w.render();
            checkWidgetCommon(w);

            w.$('.s-select-file-button').click();
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            expect(arg.parentModel).toBe(admin);
            arg.onItemClick(item);
            arg.parentView._validate();
        });
        waitsFor(function () {
            return w.model && w.model.value() && w.model.value().name() === 'b';
        });
        runs(function () {
            expect(w.model.value().name()).toBe('b');

            expect(w.model.get('path')).toEqual([]);
        });
    });

    it('file', function () {
        var arg, file, item, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget'
                })
            });

            w.render();
            checkWidgetCommon(w);

            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 5) === 'file/') {
                    return $.Deferred().resolve(file.toJSON());
                }
                return $.Deferred().resolve([file.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
            expect(arg.parentModel).toBe(admin);
            arg.onItemClick(item);
            arg.parentView._validate();
        });
        waitsFor(function () {
            return w.model && w.model.value() && w.model.value().name() === 'e';
        });
        runs(function () {
            expect(w.model.value().name()).toBe('e');
            expect(w.model.get('path')).toEqual([]);
        });
    });

    it('file default', function () {
        var w, folder;
        runs(function () {
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f' });

            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.data.public === false) {
                    // simulate no private
                    return $.Deferred().resolve([]);
                }
                return $.Deferred().resolve([folder.toJSON()]);
            });
            spyOn(girder.auth, 'getCurrentUser').andCallFake(function () {
                return admin;
            });

            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    extensions: '.png',
                    required: true,
                    channel: 'output'
                }),
                setDefaultOutput: 't'
            });

            w.render();
            checkWidgetCommon(w);
        });
        waitsFor(function () {
            return w.model.value() && w.model.value().name().startsWith('t');
        });
        runs(function () {
            expect(w.model.value().name()).toMatch(/t-Title-.*\.png/);
            expect(w.model.get('parent').name()).toBe('f');
            expect(w.model.get('path')).toEqual(['f', w.model.value().name()]);
        });
    });

    it('image', function () {
        var arg, item, file, w;
        runs(function () {
            file = new girder.models.FileModel({_id: 'file id', name: 'g'});
            item = new girder.models.ItemModel({
                _id: 'item id', name: 'f', largeImage: {fileId: file.id}});

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};

            w = new slicer.views.ControlWidget({
                parentView: parentView,
                rootPath: admin,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'image',
                    title: 'Title',
                    id: 'image-widget'
                })
            });

            w.render();
            checkWidgetCommon(w);

            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                return $.Deferred().resolve(file.toJSON());
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
            expect(arg.parentModel).toBe(admin);
            arg.onItemClick(item);
            arg.parentView._validate();

            w.remove();
        });
        waitsFor(function () {
            return w.model && w.model.value() && w.model.value().name() === 'g';
        });
        runs(function () {
            expect(w.model.value().name()).toBe('g');
            expect(w.model.get('path')).toEqual([]);
        });
    });

    it('check multi exists', function () {
            item = new girder.models.ItemModel({id: 'model id', name: 'b'});

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};

            w = new slicer.views.ControlWidget({
                parentView: parentView,
                rootPath: admin,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'item',
                    title: 'Title',
                    id: 'item-widget'
                })
            });

            w.render();
            checkWidgetCommon(w);
            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                return $.Deferred().resolve(file.toJSON());
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.remove();
    });

    it('multiple flag prevents multi', function () {
        item = new girder.models.ItemModel({id: 'model id', name: 'b'});

        hProto.initialize = function (_arg) {
            arg = _arg;
            this.breadcrumbs = [];
        };
        hProto.render = function () {};

        w = new slicer.views.ControlWidget({
            parentView: parentView,
            rootPath: admin,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'item',
                title: 'Title',
                id: 'item-widget',
                multiple: true,
            })
        });

        w.render();
        checkWidgetCommon(w);
        expect(w.$('.s-select-multifile-button').length).toBe(0);
        w.remove();
    });

    it('multi type swapping', function () {
        girderTest.waitForLoad('wait 1');
        runs(function() {
            item = new girder.models.ItemModel({id: 'model id', name: 'b'});

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};

            w = new slicer.views.ControlWidget({
                parentView: parentView,
                rootPath: admin,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'item',
                    title: 'Title',
                    id: 'item-widget',
                })
            });

            w.render();
            checkWidgetCommon(w);
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-multifile-button').click();
        });
        girderTest.waitForDialog('wait 2');
        waitsFor(function () {
            return $('.modal-footer a.btn-default').length === 1;
        }, 'default button to show');
        runs(function() {
            expect(w.model.get('type')).toBe('multi');
            expect(w.model.get('defaultType')).toBe('item');
            $('.modal-footer a.btn-default').click();
        });
        girderTest.waitForLoad('wait 3');
        waitsFor(function () {
            return $('.modal-dialog:visible').length === 0;
        }, 'modal to hide');
        runs(function() {
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return $('.modal-dialog:visible').length === 1;
        }, 'modal to show');
        runs(function() {
            $('.modal-footer a.btn-default').click();
            expect(w.model.get('type')).toBe('item');
            w.remove();
        });
    });

    // disabling this -- it needs to be refactored to use actual folders and
    // collections in the database, not just local javascript models
    xit('new-file', function () {
        var arg,
            hView,
            w,
            collection = new girder.models.CollectionModel({id: 'model id', name: 'b'}),
            folder = new girder.models.FolderModel({id: 'folder id', name: 'c'});

        runs(function () {
            hProto.initialize = function (_arg) {
                arg = _arg;
                hView = this;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                parentView: parentView,
                rootPath: admin,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'new-file',
                    title: 'Title',
                    id: 'file-widget'
                })
            });

            w.render();
            checkWidgetCommon(w);

            slicer.rootPath = {};
            expect(arg.parentModel).toBe(admin);

            // selecting without a file name entered should error
            $('.modal-dialog .g-submit-button').click();
            expect($('.g-validation-failed-message').hasClass('hidden')).toBe(false);

            // selecting with a file name in a collection should error
            $('.modal-dialog #g-input-element').val('my file');
            var r = []; for (var prop in hView.parentView) r.push(prop);
            hView.parentView._selectedItem(collection);
            hView.parentModel = collection;
            hView.parentView._validate();
            expect($('.g-validation-failed-message').hasClass('hidden')).toBe(false);

            // selecting a file in a folder should succeed
            hView.parentView._selectedItem(folder);
            hView.parentModel = folder;
            hView.parentView._validate();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').hasClass('hidden') && w.model.get('value') && w.model.get('value').get('name') === 'my file';
        });
        runs(function () {
            expect($('.g-validation-failed-message').hasClass('hidden')).toBe(true);
            expect(w.model.get('path')).toEqual([]);
            expect(w.model.get('value').get('name')).toBe('my file');
            w.remove();
        });
    });

    it('invalid', function () {
        var w = new slicer.views.ControlWidget({
            parentView: parentView,
            el: $el.get(0),
            model: new slicer.models.WidgetModel({
                type: 'invalid',
                title: 'Title',
                id: 'invalid-widget'
            })
        });
        var _warn = console.warn;
        var message;
        console.warn = function (m) { message = m; };

        w.render();
        expect(message).toBe('Invalid widget type "invalid"');
        console.warn = _warn;
    });
});

describe('control widget getRoot', function () {
    var $el, admin, hInit, hRender, hProto, parentView = {
        registerChildView: function () { }
    };

    var initializationSettings;

    function checkWidgetCommon(widget) {
        var model = widget.model;
        expect(widget.$('label[for="' + model.id + '"]').text())
            .toBe(model.get('title'));
        if (widget.model.isEnumeration()) {
            expect(widget.$('select#' + model.id).length).toBe(1);
        } else {
            expect(widget.$('input#' + model.id).length).toBe(1);
        }
    }

    function fakeCompleteInitialization(settings) {
        initializationSettings = settings;
    }

    beforeEach(function () {
        admin = new girder.models.UserModel({ _id: 'admin', name: 'admin' });
        hProto = girder.views.widgets.HierarchyWidget.prototype;
        hInit = hProto.initialize;
        hRender = hProto.render;
        spyOn(slicer.views.ControlWidget.prototype, 'completeInitialization').andCallFake(fakeCompleteInitialization);

        $el = $('<div/>').appendTo('body');
    });

    afterEach(function () {
        hProto.initialize = hInit;
        hProto.render = hRender;
        $el.remove();
    });


    it('itemId', function () {
        var arg, file, item, folder, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd', folderId: 'folder id'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin', parentCollection:'user' });

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    value: new girder.models.ItemModel({
                        "itemId": 'item id',
                        name: 'd'
                    })
                })
            });

            w.render();
            checkWidgetCommon(w);
            initializationSettings = false;


            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 11) === 'collection/'){
                    return $.Deferred().resolve(admin.toJSON());
                }
                if (opts.url.substr(0, 5) === 'item/') {
                    return $.Deferred().resolve(item.toJSON());
                }
                if (opts.url.substr(0, 7) === 'folder/') {
                    return $.Deferred().resolve(folder.toJSON());
                }
                return $.Deferred().resolve([item.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return initializationSettings !== false;
        }, 'the initialization settings to change');
        runs(function () {
            expect(initializationSettings.root.get('_id')).toBe(folder.get('_id'))

        }, 'folder should be the root');
    });

    it('folderId', function () {
        var arg, file, item, folder, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd', folderId: 'folder id'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin' });

            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    value: new girder.models.ItemModel({
                        "folderId": 'folder id',
                        name: 'regex'
                    })
                })
            });

            w.render();
            checkWidgetCommon(w);
            initializationSettings = false;


            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 11) === 'collection/'){
                    return $.Deferred().resolve(admin.toJSON());
                }
                if (opts.url.substr(0, 5) === 'item/') {
                    return $.Deferred().resolve(item.toJSON());
                }
                if (opts.url.substr(0, 7) === 'folder/') {
                    return $.Deferred().resolve(folder.toJSON());
                }
                return $.Deferred().resolve([item.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return initializationSettings !== false;
        }, 'the initialization settings to change');
        runs(function () {
            expect(initializationSettings.root.get('_id')).toBe(folder.get('_id'))

        }, 'folder should be the root');
    });

    it('parentCollection', function () {
        var arg, file, item, folder, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd', folderId: 'folder id'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin', parentCollection:'user' });
            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    value: new girder.models.ItemModel({
                        'parentCollection': 'user',
                        'parentId': 'admin',
                    })
                })
            });

            w.render();
            checkWidgetCommon(w);
            initializationSettings = false;


            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 11) === 'collection/'){
                    return $.Deferred().resolve(user.toJSON());
                }
                if (opts.url.substr(0, 5) === 'item/') {
                    return $.Deferred().resolve(item.toJSON());
                }
                if (opts.url.substr(0, 7) === 'folder/') {
                    return $.Deferred().resolve(folder.toJSON());
                }
                return $.Deferred().resolve([item.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return initializationSettings !== false;
        }, 'the initialization settings to change');
        runs(function () {
            expect(initializationSettings.root.get('_id')).toBe(admin.get('_id'))

        }, 'admin should be the root');
    });

    it('itemId error root test', function () {
        var arg, file, item, folder, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd', folderId: 'folder id'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin', parentCollection:'user' });
            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    value: new girder.models.ItemModel({
                        "itemId": 'fake item id',
                        name: 'd'
                    })
                })
            });

            w.render();
            checkWidgetCommon(w);
            initializationSettings = false;


            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 11) === 'collection/'){
                    return $.Deferred().resolve(user.toJSON());
                }
                if (opts.url.substr(0, 5) === 'item/') {
                    return $.Deferred().reject(item.toJSON());
                }
                if (opts.url.substr(0, 7) === 'folder/') {
                    return $.Deferred().resolve(folder.toJSON());
                }
                return $.Deferred().resolve([item.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return initializationSettings !== false;
        }, 'the initialization settings to change');
        runs(function () {
            expect(initializationSettings.root).toBe(null);

        }, 'root should be null');
    });

    it('folderId error root test', function () {
        var arg, file, item, folder, w;
        runs(function () {
            item = new girder.models.ItemModel({_id: 'item id', name: 'd', folderId: 'folder id'});
            file = new girder.models.FileModel({_id: 'file id', name: 'e'});
            folder = new girder.models.FolderModel({ _id: 'folder id', name: 'f', parentId: 'admin', parentCollection:'user' });
            hProto.initialize = function (_arg) {
                arg = _arg;
                this.breadcrumbs = [];
            };
            hProto.render = function () {};
            w = new slicer.views.ControlWidget({
                rootPath: admin,
                parentView: parentView,
                el: $el.get(0),
                model: new slicer.models.WidgetModel({
                    type: 'file',
                    title: 'Title',
                    id: 'file-widget',
                    value: new girder.models.ItemModel({
                        "folderId": 'folder id',
                        name: 'd'
                    })
                })
            });

            w.render();
            checkWidgetCommon(w);
            initializationSettings = false;


            spyOn(girder.rest, 'restRequest').andCallFake(function (opts) {
                if (opts.url.substr(0, 11) === 'collection/'){
                    return $.Deferred().resolve(user.toJSON());
                }
                if (opts.url.substr(0, 5) === 'item/') {
                    return $.Deferred().resolve(item.toJSON());
                }
                if (opts.url.substr(0, 7) === 'folder/') {
                    return $.Deferred().reject(folder.toJSON());
                }
                return $.Deferred().resolve([item.toJSON()]);
            });
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-file-button').click();
        });
        waitsFor(function () {
            return initializationSettings !== false;
        }, 'the initialization settings to change');
        runs(function () {
            expect(initializationSettings.root).toBe(null);

        }, 'root should be null');
    });


});
