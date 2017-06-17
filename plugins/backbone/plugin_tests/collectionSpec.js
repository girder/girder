girderTest.importPlugin('backbone');
girderTest.addScript('/plugins/backbone/plugin_tests/helper.js');

describe('collection', function () {
    var CollectionCollection, CollectionModel, model;
    beforeEach(function () {
        CollectionCollection = girder.plugins.backbone.collections.CollectionCollection;
        CollectionModel = girder.plugins.backbone.models.CollectionModel;
    });
    it('login', function () {
        testHelper.login();
    });
    describe('CRUD', function () {
        it('model save new', function () {
            testHelper.test(function () {
                model = new CollectionModel({
                    name: 'test',
                    description: 'test save collection',
                    public: true
                });
                return model.save()
                    .done(function () {
                        expect(model.id).toBeDefined();
                        expect(model.get('name')).toBe('test');
                        expect(model.get('public')).toBe(true);
                        expect(model.get('description')).toBe('test save collection');
                    });
            });
        });
        it('model fetch', function () {
            testHelper.test(function () {
                var other = new CollectionModel({_id: model.id});
                return other.fetch().done(function () {
                    testHelper.equal(other.attributes, model.attributes);
                });
            });
        });
        it('collection fetch', function () {
            testHelper.test(function () {
                var collection = new CollectionCollection();
                return collection.fetch()
                    .done(function () {
                        expect(collection.pluck('name')).toEqual(['c1', 'c2', 'c3', 'test']);
                    });
            });
        });
        it('model save update', function () {
            model.set('name', 'other');
            return model.save({wait: true})
                .done(function () {
                    expect(model.get('name')).toBe('other');
                });
        });
        it('model destroy', function () {
            return model.destroy();
        });
    });
    describe('hierarchy methods', function () {
        it('fetch c1', function () {
            testHelper.test(function () {
                var collection = new CollectionCollection();
                return collection.fetch({data: {text: 'c1'}})
                    .then(function () {
                        expect(collection.size()).toBe(1);
                        model = collection.models[0];
                        return model.fetch();
                    });
            });
        });
        it('parent', function () {
            expect(model.parent()).toBe(null);
        });
        it('children', function () {
            testHelper.test(function () {
                var children = model.children();
                expect(children.length).toBe(1);

                var folders = children[0];
                expect(folders.resource).toBe('folder');
                return folders.fetch().done(function () {
                    expect(folders.pluck('name'))
                        .toEqual(['f1', 'f2', 'f3']);
                });
            });
        });
    });
});
