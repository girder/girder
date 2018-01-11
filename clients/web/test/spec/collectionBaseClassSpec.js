girderTest.startApp();

function canary() {
    var isDone = false;
    var result = function done() {
        if (this === result) { /* done.check() */
            return isDone;
        }

        isDone = true;
    };
    result.check = result.bind(result);

    return result;
}

var failIfError = function (error) { expect(error).toBeUndefined(); };

var reFiltered = /filterTest(\d+)/;

describe('Pre-test setup', function () {
    it('register a user (first is admin)',
        girderTest.createUser('admin',
            'admin@email.com',
            'Admin',
            'Admin',
            'adminpassword!',
            []));
});

describe('Test normal collection operation', function () {
    it('create several dummy api keys', function () {
        var done = canary();

        var createPromise = $.when(
            new girder.models.ApiKeyModel({ name: 'test0' }).save(),
            new girder.models.ApiKeyModel({ name: 'test1' }).save(),
            new girder.models.ApiKeyModel({ name: 'test2' }).save(),
            new girder.models.ApiKeyModel({ name: 'test3' }).save(),
            new girder.models.ApiKeyModel({ name: 'test4' }).save(),
            new girder.models.ApiKeyModel({ name: 'test5' }).save(),
            new girder.models.ApiKeyModel({ name: 'test6' }).save(),
            new girder.models.ApiKeyModel({ name: 'test7' }).save(),
            new girder.models.ApiKeyModel({ name: 'test8' }).save(),
            new girder.models.ApiKeyModel({ name: 'test9' }).save()
        );

        var collection;

        var fetchPromise = createPromise.then(function () {
            collection = new girder.collections.ApiKeyCollection();

            /* pageLimit shouldn't matter; we should only get ten entries */
            collection.pageLimit = 100;
            return collection.fetch();
        });

        $.when(createPromise, fetchPromise).done(function () {
            expect(collection.length).toBe(10);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });

    it('ensure collection fetch fires backbone "reset" event with expected options', function () {
        var done = canary();
        var collection = new girder.collections.ApiKeyCollection();
        var previousModels = null;

        // Within a "reset" event, Backbone provides the list of previous models
        // as options.previousModels.
        collection.once('reset', function (collection, options) {
            previousModels = options.previousModels;
        });

        collection.fetch()
            .fail(failIfError)
            .always(done);

        waitsFor(done.check, 'to be done');

        runs(function () {
            expect(collection.length).toBe(10);
            expect(Array.isArray(previousModels)).toBe(true);
            expect(previousModels.length).toBe(0);
        });
    });

    it('ensure collections can go backwards and forwards', function () {
        var done = canary();
        var collection = new girder.collections.ApiKeyCollection();

        collection.pageLimit = 2;
        collection.append = false;

        collection.fetchNextPage().then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test0');
            expect(collection.at(1).get('name')).toBe('test1');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(false);
            expect(collection.offset).toBe(2);
            expect(collection.pageNum()).toBe(0);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test2');
            expect(collection.at(1).get('name')).toBe('test3');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(4);
            expect(collection.pageNum()).toBe(1);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test4');
            expect(collection.at(1).get('name')).toBe('test5');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(6);
            expect(collection.pageNum()).toBe(2);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test6');
            expect(collection.at(1).get('name')).toBe('test7');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(8);
            expect(collection.pageNum()).toBe(3);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test8');
            expect(collection.at(1).get('name')).toBe('test9');
            expect(collection.hasNextPage()).toBe(false);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(10);
            expect(collection.pageNum()).toBe(4);

            return collection.fetchPreviousPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test6');
            expect(collection.at(1).get('name')).toBe('test7');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(8);
            expect(collection.pageNum()).toBe(3);

            return collection.fetchPreviousPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test4');
            expect(collection.at(1).get('name')).toBe('test5');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(6);
            expect(collection.pageNum()).toBe(2);

            return collection.fetchPreviousPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test2');
            expect(collection.at(1).get('name')).toBe('test3');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(4);
            expect(collection.pageNum()).toBe(1);

            return collection.fetchPreviousPage();
        }).done(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('test0');
            expect(collection.at(1).get('name')).toBe('test1');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(false);
            expect(collection.offset).toBe(2);
            expect(collection.pageNum()).toBe(0);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });
});

describe('Test collection filtering', function () {
    it('create several dummy api keys', function () {
        var done = canary();

        var createPromise = $.when(
            new girder.models.ApiKeyModel({ name: 'filterTest0' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest1' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest2' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest3' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest4' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest5' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest6' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest7' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest8' }).save(),
            new girder.models.ApiKeyModel({ name: 'filterTest9' }).save()
        );

        var filteredCollection;

        var fetchPromise = createPromise.then(function () {
            filteredCollection = new girder.collections.ApiKeyCollection();

            filteredCollection.filterFunc = function (apiKey) {
                return apiKey.name.match(reFiltered);
            };

            /* pageLimit shouldn't matter; we should only get ten entries */
            filteredCollection.pageLimit = 100;
            return filteredCollection.fetch();
        });

        $.when(createPromise, fetchPromise).done(function () {
            expect(filteredCollection.length).toBe(10);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });

    it('select only dummy api keys with even index', function () {
        var done = canary();
        var collection = new girder.collections.ApiKeyCollection();
        collection.filterFunc = function (apiKey) {
            var match = apiKey.name.match(reFiltered);
            if (match) {
                match = parseInt(match[1]) % 2 === 0;
            }
            return match;
        };

        collection.fetch().done(function () {
            expect(collection.length).toBe(5);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });

    it('select only dummy api keys outside a given range', function () {
        var done = canary();
        var collection = new girder.collections.ApiKeyCollection();
        collection.filterFunc = function (apiKey) {
            var match = apiKey.name.match(reFiltered);
            var index;
            if (match) {
                index = parseInt(match[1]);
                match = index < 3 || index > 6;
            }
            return match;
        };

        /*
         * in this case,
         *   - entries 0-4 should be fetched
         *   - entries 0, 1, and 2 should be included in the page
         *   - entries 3 and 4 should be excluded by the filter
         *   - entries 5-9 should be fetched
         *   - entries 5 and 6 should be excluded by the filter
         *   - entries 7 and 8 should complete the page
         *   - the collection should have more pages remaining, since entry 9
         *     had not yet been included
         */
        collection.pageLimit = 5;
        collection.fetch().done(function () {
            expect(collection.length).toBe(5);
            expect(collection.at(0).get('name')).toBe('filterTest0');
            expect(collection.at(1).get('name')).toBe('filterTest1');
            expect(collection.at(2).get('name')).toBe('filterTest2');
            expect(collection.at(3).get('name')).toBe('filterTest7');
            expect(collection.at(4).get('name')).toBe('filterTest8');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.offset).toBe(9);
            expect(collection.pageNum()).toBe(0);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });

    it('ensure filtered collections can go backwards and forwards', function () {
        var done = canary();
        var collection = new girder.collections.ApiKeyCollection();
        collection.filterFunc = function (apiKey) {
            var match = apiKey.name.match(reFiltered);
            if (match) {
                var index = parseInt(match[1]);
                match = index < 3 || index > 6;
            }
            return match;
        };

        collection.pageLimit = 2;
        collection.append = false;

        collection.fetchNextPage().then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('filterTest0');
            expect(collection.at(1).get('name')).toBe('filterTest1');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(false);
            expect(collection.offset).toBe(2);
            expect(collection.pageNum()).toBe(0);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('filterTest2');
            expect(collection.at(1).get('name')).toBe('filterTest7');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(8);
            expect(collection.pageNum()).toBe(1);

            return collection.fetchNextPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('filterTest8');
            expect(collection.at(1).get('name')).toBe('filterTest9');
            /* true because the collection hasn't checked every record, yet */
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(10);
            expect(collection.pageNum()).toBe(2);

            return collection.fetchPreviousPage();
        }).then(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('filterTest2');
            expect(collection.at(1).get('name')).toBe('filterTest7');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(true);
            expect(collection.offset).toBe(8);
            expect(collection.pageNum()).toBe(1);

            return collection.fetchPreviousPage();
        }).done(function () {
            expect(collection.length).toBe(2);
            expect(collection.at(0).get('name')).toBe('filterTest0');
            expect(collection.at(1).get('name')).toBe('filterTest1');
            expect(collection.hasNextPage()).toBe(true);
            expect(collection.hasPreviousPage()).toBe(false);
            expect(collection.offset).toBe(2);
            expect(collection.pageNum()).toBe(0);
        }).fail(failIfError).always(done);

        waitsFor(done.check, 'to be done');
    });
});
