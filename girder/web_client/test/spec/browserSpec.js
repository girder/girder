describe('Test the hierarchy browser modal', function () {
    var testEl;
    var returnVal;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        returnVal = null;

        spyOn(girder.rest, 'restRequest').andCallFake(function () {
            return $.Deferred().resolve(returnVal).promise();
        });
        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        girder.auth.logout();
        $.support.transition = transition;
    });

    describe('root selection', function () {
        it('defaults', function () {
            returnVal = [];

            var view;
            runs(function () {
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null
                });
                // RootSelectorWidget will self-render, as soon as its initial 'fetch()' completes

                // We should be able to attach a spy to 'view.render' without a race condition, as
                // long as we do it before returning to the main event loop (where async results
                // from 'fetch()' might already be pending)
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                // 'view.render' will be called once for each of 'view.groups', and 'view.groups'
                // has 2 collections here, so rendering should only be considered finished once all
                // complete
                return view.render.callCount >= 2;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.find('option').first().text()).toBe('Select a root...');
                expect(select.find('optgroup[label="Collections"]').length).toBe(1);
                expect(select.find('optgroup[label="Users"]').length).toBe(1);
            });
        });

        it('display order', function () {
            returnVal = [];

            var view;
            runs(function () {
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    display: ['Users']
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 2;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.find('option').first().text()).toBe('Select a root...');
                expect(select.find('optgroup[label="Collections"]').length).toBe(0);
                expect(select.find('optgroup[label="Users"]').length).toBe(1);
            });
        });

        it('user logged in', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));
            returnVal = [];

            var view;
            runs(function () {
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 2;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.find('option').first().text()).toBe('Select a root...');
                expect(select.find('option[value="0"]').text()).toBe('Home');
            });
        });

        it('rerender on login', function () {
            returnVal = [];
            var user = {
                user: {
                    _id: '0',
                    login: 'johndoe',
                    firstName: 'John',
                    lastName: 'Doe'
                },
                authToken: {
                    token: ''
                }
            };
            girder.rest.restRequest.andCallFake(function (params) {
                if (params.url === '/user/authentication') {
                    // The return value for the initial login call
                    return $.Deferred().resolve(user).promise();
                }

                // After login return an empty array for collection fetches
                // on the RootSelector
                return $.Deferred().resolve([]).promise();
            });

            var view;
            runs(function () {
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 2;
            });

            runs(function () {
                view.render.reset();
                girder.auth.login('johndoe', 'password');
            });

            waitsFor(function () {
                return view.render.callCount >= 2;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.find('option').first().text()).toBe('Select a root...');
                expect(select.find('option[value="0"]').text()).toBe('Home');
            });
        });

        it('custom optgroup', function () {
            var col;
            var view;

            runs(function () {
                returnVal = [];
                col = new girder.collections.CollectionCollection();

                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Collections', 'Custom']
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.find('option').first().text()).toBe('Select a root...');
                expect(select.find('optgroup').first().prop('label')).toBe('Collections');
                expect(select.find('optgroup').eq(1).prop('label')).toBe('Custom');

                returnVal = [
                    { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                    { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                    { _id: '123', name: 'custom 3', _modelType: 'folder' }
                ];
                view.render.reset();
                col.fetch();
            });

            waitsFor(function () {
                return view.render.callCount >= 1;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                var opt = select.find('optgroup[label="Custom"] > option[value="abc"]');
                expect(opt.data('group')).toBe('Custom');
                expect(opt.text()).toBe('custom 1');

                opt = select.find('optgroup[label="Custom"] > option[value="def"]');
                expect(opt.data('group')).toBe('Custom');
                expect(opt.text()).toBe('thelogin');

                opt = select.find('optgroup[label="Custom"] > option[value="123"]');
                expect(opt.data('group')).toBe('Custom');
                expect(opt.text()).toBe('custom 3');
            });
        });

        it('respond to user selection', function () {
            var col;
            var view;

            runs(function () {
                returnVal = [
                    { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                    { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                    { _id: '123', name: 'custom 3', _modelType: 'folder' }
                ];
                col = new girder.collections.CollectionCollection();
                col.fetch();
            });

            waitsFor(function () {
                return col.size() === 3;
            });

            runs(function () {
                returnVal = [];

                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Collections', 'Custom']
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var called = 0;
                view.on('g:selected', function (evt) {
                    expect(evt.root.attributes).toEqual({
                        _id: '123',
                        name: 'custom 3',
                        _modelType: 'folder'
                    });
                    called += 1;
                });

                view.$('select').val('123').trigger('change');
                // Assume that the 'change' event propagates synchronously
                expect(called).toBe(1);
            });
        });

        it('respond to Home selection', function () {
            var col;
            var view;
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            runs(function () {
                returnVal = [
                    { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                    { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                    { _id: '123', name: 'custom 3', _modelType: 'folder' }
                ];
                col = new girder.collections.CollectionCollection();
                col.fetch();
            });

            waitsFor(function () {
                return col.size() === 3;
            });

            runs(function () {
                returnVal = [];

                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Home', 'Collections', 'Custom']
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var called = 0;
                view.on('g:selected', function (evt) {
                    expect(evt.root.attributes).toEqual({
                        _id: '0',
                        login: 'johndoe',
                        firstName: 'John',
                        lastName: 'Doe'
                    });
                    called += 1;
                });

                view.$('select').val('0').trigger('change');
                // Assume that the 'change' event propagates synchronously
                expect(called).toBe(1);
            });
        });

        it('preselected option', function () {
            var col;
            var view;
            returnVal = [
                { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                { _id: '123', name: 'custom 3', _modelType: 'folder' }
            ];

            runs(function () {
                col = new girder.collections.CollectionCollection();
                col.fetch();
            });

            waitsFor(function () {
                return col.size() === 3;
            });

            runs(function () {
                returnVal = [];
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Collections', 'Custom'],
                    selected: col.models[2]
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.val()).toBe('123');
            });
        });

        it('preselected by Resource Option (object or Model)', function () {
            var col;
            var view;
            returnVal = [
                { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                { _id: '123', name: 'custom 3', _modelType: 'custom' }
            ];

            runs(function () {
                col = new girder.collections.CollectionCollection();
                col.fetch();
            });

            waitsFor(function () {
                return col.size() === 3;
            });

            runs(function () {
                returnVal = [];
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Collections', 'Custom'],
                    selectByResource: { attributes: { baseParentId: 'def' } }
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.val()).toBe('def');
            });
        });

        it('preselected by Resource Option (String Id)', function () {
            var col;
            var view;
            returnVal = [
                { _id: 'abc', name: 'custom 1', _modelType: 'collection' },
                { _id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin' },
                { _id: '123', name: 'custom 3', _modelType: 'custom' }
            ];

            runs(function () {
                col = new girder.collections.CollectionCollection();
                col.fetch();
            });

            waitsFor(function () {
                return col.size() === 3;
            });

            runs(function () {
                returnVal = [];
                view = new girder.views.widgets.RootSelectorWidget({
                    el: testEl,
                    parentView: null,
                    groups: {
                        Custom: col
                    },
                    display: ['Collections', 'Custom'],
                    selectByResource: '123'
                });
                spyOn(view, 'render').andCallThrough();
            });

            waitsFor(function () {
                return view.render.callCount >= 3;
            });

            runs(function () {
                var select = view.$('select#g-root-selector');
                expect(select.length).toBe(1);
                expect(select.val()).toBe('123');
            });
        });
    });

    describe('browser modal', function () {
        var view;

        var hwSettings;
        function fakeInitialize(settings) {
            hwSettings = settings;
            this.parentModel = settings.parentModel;
        }

        beforeEach(function () {
            testEl.addClass('modal');
            spyOn(girder.views.widgets.HierarchyWidget.prototype, 'render');
            spyOn(girder.views.widgets.HierarchyWidget.prototype, 'initialize').andCallFake(fakeInitialize);
        });
        afterEach(function () {
            if (view) {
                view.$el.modal('hide');
            }
        });
        it('defaults', function () {
            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl
            }).render();

            expect(view.$('.modal-title').text()).toBe('Select an item');
            expect(view.$('#g-root-selector').length).toBe(1);

            waitsFor(function () {
                return $(view.$el).is(':visible');
            });
            runs(function () {
                view.$('a:contains(Cancel)').trigger('click');
                expect($(view.$el).is(':visible')).toBe(false);
            });
        });

        it('preview off', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                showPreview: false
            }).render();

            waitsFor(function () {
                return $(view.$el).is(':visible');
            });
            runs(function () {
                view.$('#g-root-selector').val('0').trigger('change');
                expect(view.$('#g-selected-model').length).toBe(0);
            });
        });

        it('validation', function () {
            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                validate: function (val) {
                    return $.Deferred().reject('invalid').promise();
                }
            }).render();
            waitsFor(function () {
                return $(view.$el).is(':visible');
            });
            runs(function () {
                view.$('.g-submit-button').trigger('click');
            });
            waitsFor(function () {
                return $('.g-validation-failed-message').text();
            }, 'validation to fail');
            runs(function () {
                expect(view.$el.hasClass('in')).toBe(true);
                expect(view.$('.g-validation-failed-message').text()).toBe('invalid');
                expect(view.$('.g-validation-falied-message').hasClass('hidden')).toBe(false);
            });
        });

        it('render hierarchy', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            var folderModel = new girder.models.FolderModel({
                _id: '1',
                name: 'my folder'
            });

            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                showItems: false,
                titleText: 'This is a title',
                rootSelectorSettings: {
                    display: ['Home']
                }
            }).render();

            expect(view.$('.modal-title').text()).toBe('This is a title');
            view.$('#g-root-selector').val('0').trigger('change');

            expect(hwSettings.parentModel).toBe(girder.auth.getCurrentUser());
            expect(view.$('g-hierarchy-widget-container').hasClass('hidden')).toBe(false);
            expect(view.$('#g-selected-model').val()).toBe('');

            view._hierarchyView.parentModel = folderModel;
            view._hierarchyView.trigger('g:setCurrentModel');
            expect(view.$('#g-selected-model').val()).toBe(folderModel.get('name'));

            var ncalls = 0;
            view.on('g:saved', function (model) {
                ncalls += 1;
                expect(model.id).toBe(folderModel.id);
            });

            waitsFor(function () {
                return $(view.$el).is(':visible');
            });

            runs(function () {
                view.$('.g-submit-button').trigger('click');
            });
            waitsFor(function () {
                return !$(view.$el).is(':visible');
            });
            runs(function () {
                expect(ncalls).toBe(1);
            });
        });

        it('item selection', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                selectItem: true,
                root: girder.auth.getCurrentUser(),
                rootSelectorSettings: {
                    display: ['Home']
                }
            }).render();

            var itemModel = new girder.models.ItemModel({
                _id: '1',
                name: 'my item'
            });

            waitsFor(function () {
                return $(view.$el).is(':visible');
            });

            runs(function () {
                expect(view.selectedModel()).toBe(null);
                view.$('#g-root-selector').val('0').trigger('change').trigger('select');
                hwSettings.onItemClick(itemModel);
                expect(view.selectedModel().id).toBe('1');
            });
        });

        it('input element', function () {
            var validateCalledWith, validateReturn, submitCalled = false;

            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                root: girder.auth.getCurrentUser(),
                input: {
                    label: 'label',
                    default: 'default',
                    placeholder: 'placeholder',
                    validate: function (val) {
                        var isValid = $.Deferred();
                        validateCalledWith = val;
                        if (validateReturn) {
                            isValid.reject(validateReturn);
                        } else {
                            isValid.resolve();
                        }
                        return isValid.promise();
                    }
                }
            }).render();

            waitsFor(function () {
                return $(view.$el).is(':visible');
            });
            runs(function () {
                validateReturn = 'invalid';

                // test form elements
                expect(view.$('#g-input-element').attr('placeholder')).toBe('placeholder');
                expect(view.$('#g-input-element').val()).toBe('default');
                expect(view.$('.g-input-element > label').text()).toBe('label');

                // test an invalid input
                view.$('#g-input-element').val('input value');
                view.$('.g-submit-button').trigger('click');
            });
            waitsFor(function () {
                return $('.g-validation-failed-message').text();
            }, 'validation to fail');
            runs(function () {
                expect(validateCalledWith).toBe('input value');
                expect(view.$('.g-validation-failed-message').text()).toBe('invalid');
                expect(view.$('.g-validation-failed-message').hasClass('hidden')).toBe(false);

                // test a valid input
                view.on('g:saved', function (model, input) {
                    expect(input).toBe('input value');
                    submitCalled = true;
                });
                validateReturn = undefined;
                view.$('#g-input-element').val('input value');
                view.$('.g-submit-button').trigger('click');
            });

            waitsFor(function () {
                return submitCalled;
            });
        });
    });
});

describe('browser hierarchy selection', function () {
    var user, folder, subfolder, item, widget;
    var testEl;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        $('.modal').remove();
        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        $('.modal').remove();
        $.support.transition = transition;
    });
    it('register a user', function () {
        runs(function () {
            var _user = new girder.models.UserModel({
                login: 'mylogin',
                password: 'mypassword',
                email: 'email@girder.test',
                firstName: 'First',
                lastName: 'Last'
            }).on('g:saved', function () {
                user = _user;
            });

            _user.save();
        });

        waitsFor(function () {
            return !!user;
        }, 'user registration');
    });

    it('create top level folder', function () {
        runs(function () {
            var _folder = new girder.models.FolderModel({
                parentType: 'user',
                parentId: user.get('_id'),
                name: 'top level folder'
            }).on('g:saved', function () {
                folder = _folder;
            });

            _folder.save();
        });

        waitsFor(function () {
            return !!folder;
        }, 'folder creation');
    });

    it('create subfolder', function () {
        runs(function () {
            var _subfolder = new girder.models.FolderModel({
                parentType: 'folder',
                parentId: folder.get('_id'),
                name: 'subfolder'
            }).on('g:saved', function () {
                subfolder = _subfolder;
            });

            _subfolder.save();
        });

        waitsFor(function () {
            return !!subfolder;
        }, 'subfolder creation');
    });

    it('create item', function () {
        runs(function () {
            var _item = new girder.models.ItemModel({
                folderId: folder.get('_id'),
                name: 'an item'
            }).on('g:saved', function () {
                item = _item;
            });

            _item.save();
        });

        waitsFor(function () {
            return !!item;
        }, 'item creation');
    });

    it('test custom hierarchy widget options [file] - highlighted', function () {
        runs(function () {
            $('body').off();

            widget = new girder.views.widgets.HierarchyWidget({
                el: testEl,
                parentModel: folder,
                onItemClick: function (item) {
                    widget.selectItem(item);
                },
                showActions: false,
                parentView: null,
                highlightItem: true,
                defaultSelectedResource: item
            });
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            var link = $('.g-item-list-entry.g-selected a.g-item-list-link').attr('href').replace('#item/', '');
            expect(link).toBe(item.get('_id'));
        });
    });

    it('test browserwidget defaultSelectedResource [file]', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: item,
                selectItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('an item');
        });
    });

    it('test browserwidget defaultSelectedResource [file] - highlighted', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: item,
                selectItem: true,
                showItems: true,
                highlightItem: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0 &&
                                $('.g-item-list-entry.g-selected').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('an item');
            var link = $('.g-item-list-entry.g-selected a.g-item-list-link').attr('href').replace('#item/', '');
            expect(link).toBe(item.get('_id'));
        }, 'Make sure proper item is selected');

        waitsFor(function () {
            // Double check to make sure the removal process happened correctly
            if ($('.g-hierarchy-widget-container').length > 1) {
                $('.g-hierarchy-widget-container').get(0).remove();
            }
            return $._data($('.g-hierarchy-widget-container')[0], 'events');
        }, 'waiting for the scroll events to be bound');

        runs(function () {
            var widgetcontainer = $('.g-hierarchy-widget-container');
            // There seems to be some inconsistencies with how the scroll event is bound, a double check is done
            var scrollnamespace = null;
            if ($._data(widgetcontainer[0], 'events') &&
                $._data(widgetcontainer[0], 'events').scroll &&
                $._data(widgetcontainer[0], 'events').scroll[0].namespace) {
                scrollnamespace = $._data(widgetcontainer[0], 'events').scroll[0].namespace;
                expect(scrollnamespace).toBe('observerscroll');
            } else {
                console.log('Unable to test scrollObserver binding due to phantomJS inconsistencies');
            }
            // cause a scroll event
            widgetcontainer.trigger('click');
            // check again to confirm that the bound event handler is no longer there
            scrollnamespace = $._data(widgetcontainer[0], 'events').scroll;
            expect(scrollnamespace).toBe(undefined);
        }, 'Testing that the observer disconnects properly on user interaction');
    });

    it('test browserwidget defaultSelectedResource [folder]', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: subfolder,
                selectItem: false
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('subfolder');
        });
    });

    it('test browserwidget defaultSelectedResource [item with folder selected]', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: subfolder,
                selectItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            // We should get opened the parent of subfolder so we should be able to see subfolder and other items
            expect($('.g-item-list-entry').length).toBe(1);
            expect($('.g-folder-list-entry').length).toBe(1);
            expect(widget.$('#g-selected-model').val()).toBe('subfolder');
        });
    });
});

describe('browser hierarchy paginated selection', function () {
    var user, folder, subfolder, item, widget, itemlist;
    var testEl;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        $('.modal').remove();

        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        $('.modal').remove();
        $.support.transition = transition;
    });
    it('register a user', function () {
        runs(function () {
            var _user = new girder.models.UserModel({
                login: 'mylogin2',
                password: 'mypassword',
                email: 'email2@girder.test',
                firstName: 'First',
                lastName: 'Last'
            }).on('g:saved', function () {
                user = _user;
            });

            _user.save();
        });

        waitsFor(function () {
            return !!user;
        }, 'user registration');
    });

    it('create top level folder', function () {
        runs(function () {
            var _folder = new girder.models.FolderModel({
                parentType: 'user',
                parentId: user.get('_id'),
                name: 'top level folder'
            }).on('g:saved', function () {
                folder = _folder;
            });

            _folder.save();
        });

        waitsFor(function () {
            return !!folder;
        }, 'folder creation');
    });

    it('create subfolder', function () {
        runs(function () {
            var _subfolder = new girder.models.FolderModel({
                parentType: 'folder',
                parentId: folder.get('_id'),
                name: 'subfolder'
            }).on('g:saved', function () {
                subfolder = _subfolder;
            });

            _subfolder.save();
        });

        waitsFor(function () {
            return !!subfolder;
        }, 'subfolder creation');
    });

    it('create item', function () {
        runs(function () {
            var _item = new girder.models.ItemModel({
                folderId: folder.get('_id'),
                name: 'an item'
            }).on('g:saved', function () {
                item = _item;
            });

            _item.save();
        });

        waitsFor(function () {
            return !!item;
        }, 'item creation');
    });

    it('create lots of items', function () {
        runs(function () {
            itemlist = [];
            for (var i = 0; i < 100; i++) {
                var _item = new girder.models.ItemModel({
                    folderId: folder.get('_id'),
                    name: ('item#: ' + i)
                }).on('g:saved', function () {
                    itemlist.push(_item);
                });

                _item.save();
            }
        });
        waitsFor(function () {
            return itemlist.length === 100;
        }, 'item creation');
    });

    it('test browserwidget defaultSelectedResource [item with paginated views]', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: item,
                selectItem: true,
                paginated: true,
                highlightItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0 &&
                               $('.g-hierarachy-paginated-bar').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('an item');
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('.g-hierarachy-paginated-bar').hasClass('g-hierarchy-sticky')).toBe(true);
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Make sure paginated text is displayed with proper settings');
    });
    it('test browserwidget defaultSelectedResource [second page in paginated]', function () {
        runs(function () {
            $('.modal').remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: itemlist[itemlist.length - 1],
                selectItem: true,
                paginated: true,
                highlightItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0;
        }, 'the hierarchy widget to display');

        waitsFor(function () {
            return $('#g-page-selection-input').val() === '2';
        }, 'waits for it to go to the second page');

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('item#: 99');
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('#g-page-selection-input').val()).toBe('2');
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Make sure paginated text is displayed with proper settings');

        runs(function () {
            $('.g-folder-list-link').trigger('click');
        });

        waitsFor(function () {
            return $('.g-hierarachy-paginated-bar:not(.hidden)').length === 0;
        }, 'The removal of the page selection');

        runs(function () {
            expect($('.g-hierarachy-paginated-bar:not(.hidden)').length).toBe(0);
            $('.g-breadcrumb-link[g-index="1"]').trigger('click');
        }, 'Make sure paginated text is removed when a folder has less than one page');

        waitsFor(function () {
            return $('.g-hierarachy-paginated-bar').length === 1 && $('.g-item-list-entry').length > 10;
        }, 'The removal of the page selection');

        waitsFor(function () {
            return $('#g-page-selection-input').val() === '1';
        }, 'waits for it to go to the second page');

        runs(function () {
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('.g-page-prev.disabled').length).toBe(1);
            expect($('.g-page-next.disabled').length).toBe(0);
            expect($('.g-page-next').length).toBe(1);
            expect($('#g-page-selection-input').val()).toBe('1');
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Returning to the folder should bring us to the first page');

        runs(function () {
            $('#g-page-selection-input').val(2);
            $('#g-page-selection-input').trigger('change');
        }, 'Change the page by using the input field');

        waitsFor(function () {
            return $('#g-page-selection-input:not(:disabled)').val() === '2';
        });

        runs(function () {
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('#g-page-selection-input').val()).toBe('2');
            expect($('.g-page-prev.disabled').length).toBe(0);
            expect($('.g-page-next.disabled').length).toBe(1);
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Should be on a second page now');

        runs(function () {
            $('#g-previous-paginated').click();
        }, 'Change the page by using the previous button');

        waitsFor(function () {
            return $('#g-page-selection-input:not(:disabled)').val() === '1';
        }, 'waits for it to go to the first page after clicking previous');

        runs(function () {
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('.g-page-prev.disabled').length).toBe(1);
            expect($('.g-page-next.disabled').length).toBe(0);
            expect($('.g-page-next').length).toBe(1);
            expect($('#g-page-selection-input').val()).toBe('1');
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Previous button brings us back to first page');

        runs(function () {
            $('#g-next-paginated').click();
        }, 'Change the page by using the next button');

        waitsFor(function () {
            return $('#g-page-selection-input:not(:disabled)').val() === '2';
        }, 'waits for it to go to the first page after clicking next');

        runs(function () {
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('#g-page-selection-input').val()).toBe('2');
            expect($('.g-page-prev.disabled').length).toBe(0);
            expect($('.g-page-next.disabled').length).toBe(1);
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Should be on a second page now');
    });
    it('test rejection of filterFunc while using paginated in itemListWidget', function () {
        runs(function () {
            $('.modal').remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: itemlist[itemlist.length - 1],
                selectItem: true,
                highlightItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            widget._hierarchyView.initialize({
                itemFilter: function (item) { return item; },
                parentView: widget,
                parentModel: widget.root
            });
            widget._hierarchyView.itemListView = null;
            widget._hierarchyView._initFolderViewSubwidgets();
        }, 'Creating a filterFunc to confirm it works');

        runs(function () {
            expect(widget._hierarchyView.itemListView.collection.filterFunc).toBeDefined();
        }, 'Filter Function should be set on the ItemListWidget');

        runs(function () {
            widget._hierarchyView.initialize({
                itemFilter: function (item) { return item; },
                parentView: widget,
                paginated: true,
                parentModel: widget.root
            });
            widget._hierarchyView.itemListView = null;
            widget._hierarchyView._initFolderViewSubwidgets();
        }, 'Filter Function should be false when paginated is specified during initialization');

        runs(function () {
            expect(widget._hierarchyView.itemListView._paginated).toBe(false);
            expect(widget._hierarchyView.itemListView.collection.append).toBe(true);
            expect(widget._hierarchyView.itemListView.collection.filterFunc).toBeDefined();
        }, 'Filter Function should be set on the ItemListWidget');
    });
});
