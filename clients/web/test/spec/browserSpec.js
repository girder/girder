/* globals expect, describe, it, beforeEach, afterEach */
// girderTest.startApp();

describe('Test the hierarchy browser modal', function () {
    var testEl;
    var restRequest;
    var requestArgs = [];
    var requestContext = [];
    var returnVal;
    var onRestRequest;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        restRequest = girder.rest.restRequest;
        returnVal = null;
        girder.rest.restRequest = function () {
            requestContext.push(this);
            requestArgs.push(_.toArray(arguments));
            if (onRestRequest) {
                return onRestRequest.apply(this, arguments);
            }
            return $.when(returnVal);
        };
        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        girder.auth.logout();
        girder.rest.restRequest = restRequest;
        $.support.transition = transition;
    });

    describe('root selection', function () {
        it('defaults', function () {
            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({el: testEl, parentView: null});
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
            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.find('option:eq(0)').text()).toBe('Select a root...');
            expect(select.find('option[value="0"]').text()).toBe('Home');
        });

        it('rerender on login', function () {
            returnVal = [];
            var view = new girder.views.widgets.RootSelectorWidget({
                el: testEl,
                parentView: null
            });
            returnVal = {
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
            girder.setCurrentUser(new girder.models.UserModel({
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

            var select = view.$('select#g-root-selector');
            expect(select.length).toBe(1);
            expect(select.val()).toBe('123');
        });
    });

    describe('browser modal', function () {
        var view;

        var hw;
        var hwSettings;
        var hwCalls;
        var hwView;

        beforeEach(function () {
            hw = girder.views.widgets.HierarchyWidget;
            hwCalls = 0;
            girder.views.widgets.HierarchyWidget = Backbone.View.extend({
                initialize: function (settings) {
                    hwCalls += 1;
                    hwSettings = settings;
                    hwView = this;
                    this.parentModel = settings.parentModel;
                }
            });
        });
        afterEach(function () {
            if (view) {
                view.$el.modal('hide');
            }
            girder.views.widgets.HierarchyWidget = hw;
        });
        it('defaults', function () {
            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null
            }).render();

            expect(view.$('.modal-title').text()).toBe('Select an item');
            expect(view.$('#g-root-selector').length).toBe(1);

            view.$('.g-submit-button').click();
            expect(view.$el.css('display')).toBe('none');
        });

        it('validation', function () {
            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                validate: function () {return 'invalid';}
            }).render();

            view.$('.g-submit-button').click();
            expect(view.$el.hasClass('in')).toBe(true);
            expect(view.$('.g-validation-failed-message').text()).toBe('invalid');
            expect(view.$('.g-validation-falied-message').hasClass('hidden')).toBe(false);
        });

        it('render hierarchy', function () {
            girder.auth.setCurrentUser(new girder.models.UserModel({
                _id: '0',
                login: 'johndoe',
                firstName: 'John',
                lastName: 'Doe'
            }));

            returnVal = [];
            view = new girder.views.widgets.BrowserWidget({
                parentView: null,
                helpText: 'This is helpful',
                showItems: false,
                titleText: 'This is a title',
                rootSelectorSettings: {
                    display: ['Home']
                }
            }).render();

            expect(view.$('.modal-title').text()).toBe('This is a title');
            view.$('#g-root-selector').val('0').trigger('change');

            expect(hwSettings.parentModel).toBe(girder.getCurrentUser());
            expect(view.$('g-hierarchy-widget-container').hasClass('hidden')).toBe(false);
            expect(view.$('#g-selected-model').val()).toBe(girder.getCurrentUser().id);

            var ncalls = 0;
            view.on('g:saved', function (id) {
                ncalls += 1;
                expect(id).toBe(girder.getCurrentUser().id);
            });
            view.$('.g-submit-button').click();
            expect(ncalls).toBe(1);
        });
    });
});
