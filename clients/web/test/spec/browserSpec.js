// girderTest.startApp();

describe('Test the hierarchy browser modal', function () {
    var testEl;
    var requestArgs = [];
    var requestContext = [];
    var returnVal;
    var onRestRequest;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        returnVal = null;
        onRestRequest = null;
        girder.rest.mockRestRequest(function () {
            requestContext.push(this);
            requestArgs.push(_.toArray(arguments));
            if (onRestRequest) {
                return onRestRequest.apply(this, arguments);
            }
            return $.when(returnVal);
        });
        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        girder.auth.logout();
        girder.rest.unmockRestRequest();
        $.support.transition = transition;
    });

    describe('root selection', function () {
        it('defaults', function () {
            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({el: testEl, parentView: null});
            view.render();
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('optgroup[label="Collections"]').length).toBe(1);
            expect(select.find('optgroup[label="Users"]').length).toBe(1);
        });

        it('display order', function () {
            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null,
                display: ['Users']
            });
            view.render();
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('optgroup[label="Collections"]').length).toBe(0);
            expect(select.find('optgroup[label="Users"]').length).toBe(1);
        });

        it('user logged in', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null
            });
            view.render();
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('option[value="0"]').text()).toBe('Home');
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
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null
            });
            view.render();

            onRestRequest = function (params) {
                if (params.path === '/user/authentication') {
                    // The return value for the initial login call
                    return $.when(user);
                }

                // After login return an empty array for collection fetches
                // on the RootSelector
                return $.when([]);
            };

            girder.auth.login('johndoe', 'password');

            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('option[value="0"]').text()).toBe('Home');
        });

        it('custom optgroup', function () {
            var col = new girder.collections.CollectionCollection();

            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null,
                groups: {
                    Custom: col
                },
                display: ['Collections', 'Custom']
            });
            view.render();
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('optgroup:eq(0)').prop('label')).toBe('Collections');
            expect(select.find('optgroup:eq(1)').prop('label')).toBe('Custom');

            returnVal = [
                {_id: 'abc', name: 'custom 1', _modelType: 'collection'},
                {_id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin'},
                {_id: '123', name: 'custom 3', _modelType: 'folder'}
            ];
            col.fetch();

            select = view.$('select#g-root-selector');
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

        it('respond to user selection', function () {
            returnVal = [
                {_id: 'abc', name: 'custom 1', _modelType: 'collection'},
                {_id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin'},
                {_id: '123', name: 'custom 3', _modelType: 'folder'}
            ];
            var col = new girder.collections.CollectionCollection();
            col.fetch();

            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null,
                groups: {
                    Custom: col
                },
                display: ['Collections', 'Custom']
            });
            view.render();
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
            expect(called).toBe(1);
        });

        it('respond to Home selection', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));
            returnVal = [
                {_id: 'abc', name: 'custom 1', _modelType: 'collection'},
                {_id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin'},
                {_id: '123', name: 'custom 3', _modelType: 'folder'}
            ];
            var col = new girder.collections.CollectionCollection();
            col.fetch();

            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null,
                groups: {
                    Custom: col
                },
                display: ['Home', 'Collections', 'Custom']
            });
            view.render();
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
            expect(called).toBe(1);
        });

        it('preselected option', function () {
            returnVal = [
                {_id: 'abc', name: 'custom 1', _modelType: 'collection'},
                {_id: 'def', name: 'custom 2', _modelType: 'user', login: 'thelogin'},
                {_id: '123', name: 'custom 3', _modelType: 'folder'}
            ];
            var col = new girder.collections.CollectionCollection();
            col.fetch();

            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null,
                groups: {
                    Custom: col
                },
                display: ['Collections', 'Custom'],
                selected: col.models[2]
            });
            view.render();
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.val()).toBe('123');
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
                view.$('a:contains(Cancel)').click();
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
                validate: _.constant('invalid')
            }).render();
            waitsFor(function () {
                return $(view.$el).is(':visible');
            });
            runs(function () {
                view.$('.g-submit-button').click();
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
                view.$('.g-submit-button').click();
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
                        validateCalledWith = val;
                        return validateReturn;
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
                view.$('.g-submit-button').click();

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
                view.$('.g-submit-button').click();
            });

            waitsFor(function () {
                return submitCalled;
            });
        });
    });
});
