/* global girder girderTest describe it expect beforeEach afterEach runs waitsFor _ */

girderTest.addCoveredScripts([
    '/clients/web/static/built/plugins/treeview/plugin.min.js'
]);

girderTest.importStylesheet('/static/built/plugins/treeview/plugin.min.css');

function asyncCall(func) {
    var called = false;
    var failed = false;
    runs(function () {
        func().done(function () {
            called = true;
        }).fail(function () {
            console.log('failed');
            failed = true;
        });
    });
    waitsFor(function () {
        if (failed) {
            throw new Error('Promise was rejected');
        }
        return called;
    });
}

var treeview;
beforeEach(function () {
    treeview = girder.plugins.treeview;
});

describe('treeview type registry', function () {
    it('register a new type', function () {
        var lastCall;

        function assertArguments(method, resolve) {
            return function (doc, options) {
                lastCall = method;
                expect(doc).toBe(doc);
                expect(options).toBe(options);
                return $.when(resolve);
            };
        }

        var doc = {
            type: 'testtype',
            id: 'testtypeid',
            children: false
        };
        var load = assertArguments('load', doc);
        var parent = assertArguments('parent', {id: '#', type: '#'});
        var children = assertArguments('children', []);
        var options = {};

        treeview.types.register('testtype', {
            load: load,
            parent: parent,
            children: children,
            options: options,
            icon: 'icon-test'
        });
        var def = treeview.types.getDefinition('testtype');

        expect(def.load).toBe(load);
        expect(def.parent).toBe(parent);
        expect(def.children).toBe(children);
        expect(def.options).toBe(options);
        expect(treeview.types.icons.testtype).toEqual({icons: 'icon-test'});

        expect(function () {
            treeview.types.callMethod({type: 'testtype', id: 'notanid'}, 'notamethod');
        }).toThrow();

        treeview.types.load(doc);
        expect(lastCall).toBe('load');
        expect(function () {
            treeview.types.load({type: 'notatype', id: 'notanid'});
        }).toThrow();

        treeview.types.parent(doc);
        expect(lastCall).toBe('parent');
        expect(function () {
            treeview.types.parent({type: 'notatype', id: 'notanid'});
        }).toThrow();

        treeview.types.children(doc);
        expect(lastCall).toBe('children');
        expect(function () {
            treeview.types.children({type: 'notatype', id: 'notanid'});
        }).toThrow();

        expect(treeview.types.unregister('notatype')).toBe(undefined);
        expect(treeview.types.unregister('testtype')).toBe(def);
    });

    it('register requires a load method', function () {
        expect(function () {
            treeview.types.register('invalid');
        }).toThrow();
    });

    it('node aliases', function () {
        expect(treeview.types.unalias('aliased'))
            .toBe(undefined);

        treeview.types.alias('aliased', 'home');
        expect(treeview.types.isAliased({'id': 'aliased'}))
            .toBe(true);
        expect(treeview.types.unalias('aliased'))
            .toBe('home');

        treeview.types.alias('#collections', 'home');
        asyncCall(function () {
            return treeview.types.load({id: '#collections', type: 'collections'})
                .done(function (node) {
                    expect(node.type).toBe('home');
                });
        });

        asyncCall(function () {
            var doc = {
                type: 'collection',
                id: 'collection',
                node: {
                    id: 'collection',
                    name: 'collection'
                }
            };
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent.type).toBe('home');
                });
        });

        runs(function () {
            treeview.types.unalias('#collections');
        });
    });
});

describe('builtin types', function () {
    var lastRequest;
    var response;
    var onrequest;

    beforeEach(function () {
        window.girderTreeViewRest = function (opts) {
            lastRequest = opts;
            if (onrequest) {
                onrequest(opts);
            }
            return $.when(response);
        };
    });

    afterEach(function () {
        delete window.girderTreeViewRest;
        lastRequest = undefined;
        response = undefined;
        onrequest = undefined;
    });

    it('collections', function () {
        var doc = {
            id: '#collections',
            type: 'collections'
        };

        expect(treeview.builtin.collections.mutate(doc))
            .toBe(doc);

        asyncCall(function () {
            return treeview.types.load(doc)
                .done(function (node) {
                    expect(node.parent).toBe('#');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('Collections');
                });
        });

        asyncCall(function () {
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent).toBe(null);
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('collection');
                });
        });
    });

    it('users', function () {
        var doc = {
            id: '#users',
            type: 'users'
        };

        expect(treeview.builtin.users.mutate(doc))
            .toBe(doc);

        asyncCall(function () {
            return treeview.types.load(doc)
                .done(function (node) {
                    expect(node.parent).toBe('#');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('Users');
                });
        });

        asyncCall(function () {
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent).toBe(null);
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('user');
                });
        });
    });

    it('home', function () {
        var doc = {
            id: 'userid',
            type: 'home',
            model: {
                _id: 'userid',
                _modelType: 'user',
                login: 'login'
            }
        };

        asyncCall(function () {
            response = doc.model;
            return treeview.types.load(doc)
                .done(function (node) {
                    expect(node.parent).toBe('#');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('Home');
                });
        });

        asyncCall(function () {
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent).toBe(null);
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('folder');
                    expect(lastRequest.data.parentType).toBe('user');
                    expect(lastRequest.data.parentId).toBe(doc.id);
                });
        });
    });

    it('user', function () {
        var doc = {
            id: 'userid',
            type: 'user',
            model: {
                _id: 'userid',
                _modelType: 'user',
                login: 'login'
            }
        };

        asyncCall(function () {
            response = doc.model;
            return treeview.types.load(doc)
                .done(function (node) {
                    expect(node.parent).toBe('#users');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('login');
                });
        });

        asyncCall(function () {
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent.type).toBe('users');
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('folder');
                    expect(lastRequest.data.parentType).toBe('user');
                    expect(lastRequest.data.parentId).toBe(doc.id);
                });
        });
    });

    it('collection', function () {
        var doc = {
            id: 'collection',
            type: 'collection'
        };

        asyncCall(function () {
            response = _.extend(doc, {
                name: 'a'
            });

            return treeview.types.load(doc)
                .done(function (node) {
                    expect(lastRequest.path).toBe('collection/' + doc.id);
                    expect(node.parent).toBe('#collections');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('a');
                });
        });

        asyncCall(function () {
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(parent.type).toBe('collections');
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('folder');
                    expect(lastRequest.data.parentType).toBe('collection');
                    expect(lastRequest.data.parentId).toBe(doc.id);
                });
        });
    });

    it('folder', function () {
        var doc = {
            id: 'folder',
            type: 'folder',
            model: {
                _id: 'folder',
                _modelType: 'folder',
                name: 'a',
                parentCollection: 'collection',
                parentId: 'parent'
            }
        };

        expect(function () {
            treeview.types.parent({
                id: 'folder',
                type: 'folder',
                model: {
                    _id: 'folder',
                    _modelType: 'folder',
                    name: 'a',
                    parentCollection: 'invalid',
                    parentId: 'parent'
                }
            });
        }).toThrow();

        asyncCall(function () {
            response = _.extend(doc, {
                name: 'a',
                parentCollection: 'collection',
                parentId: 'ca'
            });

            return treeview.types.load(doc)
                .done(function (node) {
                    expect(lastRequest.path).toBe('folder/' + doc.id);
                    expect(node.parent).toBe('ca');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('a');
                });
        });

        asyncCall(function () {
            response = {
                _id: 'parent',
                _modelType: 'collection',
                name: 'parent'
            };
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(lastRequest.path).toBe('collection/' + doc.model.parentId);
                    expect(parent.type).toBe('collection');
                });
        });

        asyncCall(function () {
            response = {
                _id: 'parent',
                _modelType: 'user',
                name: 'parent'
            };
            doc.model.parentCollection = 'user';

            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(lastRequest.path).toBe('user/' + doc.model.parentId);
                    expect(parent.type).toBe('user');
                });
        });

        asyncCall(function () {
            response = {
                _id: 'parent',
                _modelType: 'folder',
                name: 'parent'
            };
            doc.model.parentCollection = 'folder';

            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(lastRequest.path).toBe('folder/' + doc.model.parentId);
                    expect(parent.type).toBe('folder');
                });
        });

        asyncCall(function () {
            onrequest = function (opts) {
                if (opts.path.match(/^folder/)) {
                    response = [[{
                        _id: 'childfolder',
                        _modelType: 'folder',
                        name: 'child folder',
                        parentCollection: 'folder',
                        parentId: doc.id
                    }]];
                } else {
                    response = [[{
                        _id: 'childitem',
                        _modelType: 'item',
                        name: 'child item',
                        parentCollection: 'folder',
                        parentId: doc.id
                    }]];
                }
            };
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    var child;
                    expect(children.length).toBe(2);

                    child = children[0];
                    expect(child.type).toBe('folder');
                    expect(child.id).toBe('childfolder');

                    child = children[1];
                    expect(child.type).toBe('item');
                    expect(child.id).toBe('childitem');
                });
        });
    });

    it('item', function () {
        var doc = {
            id: 'item',
            type: 'item',
            model: {
                _id: 'item',
                _modelType: 'item',
                name: 'a',
                folderId: 'folder'
            }
        };

        asyncCall(function () {
            response = _.extend({}, doc.model);

            return treeview.types.load(doc)
                .done(function (node) {
                    expect(lastRequest.path).toBe('item/' + doc.id);
                    expect(node.parent).toBe('folder');
                    expect(node.children).toBe(true);
                    expect(node.text).toBe('a');
                });
        });

        asyncCall(function () {
            response = {
                _id: 'folder',
                _modelType: 'folder',
                name: 'parent'
            };
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(lastRequest.path).toBe('folder/' + doc.model.folderId);
                    expect(parent.type).toBe('folder');
                    expect(parent.id).toBe(doc.model.folderId);
                });
        });

        asyncCall(function () {
            response = [];
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                    expect(lastRequest.path).toBe('item/' + doc.id + '/files');
                });
        });
    });

    it('file', function () {
        var doc = {
            id: 'file',
            type: 'file',
            model: {
                _id: 'file',
                _modelType: 'file',
                name: 'a.csv',
                exts: ['csv'],
                mimeType: 'text/csv',
                itemId: 'item',
                size: 10000
            }
        };

        asyncCall(function () {
            response = _.extend({}, doc.model);

            return treeview.types.load(doc)
                .done(function (node) {
                    expect(lastRequest.path).toBe('file/' + doc.id);
                    expect(node.parent).toBe('item');
                    expect(!node.children).toBe(true);
                    expect(node.text).toBe('a.csv');
                });
        });

        asyncCall(function () {
            response = {
                _id: 'item',
                _modelType: 'item',
                name: 'parent'
            };
            return treeview.types.parent(doc)
                .done(function (parent) {
                    expect(lastRequest.path).toBe('item/' + doc.model.itemId);
                    expect(parent.type).toBe('item');
                    expect(parent.id).toBe(doc.model.itemId);
                });
        });

        asyncCall(function () {
            return treeview.types.children(doc)
                .done(function (children) {
                    expect(children).toEqual([]);
                });
        });
    });
});
