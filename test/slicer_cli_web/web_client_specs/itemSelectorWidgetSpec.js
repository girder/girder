girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();


describe('browser hierarchy paginated selection', function () {
    var user, folder, subfolder, item, widget, itemlist, parentView = {
        registerChildView: function () { }
    };
    var testEl, dialogEl;
    var transition;
    var itemSelector;

    // Uses the defaultSelectedResource of the browser widget to display properly
    function fakeselectMultiFile() {
        const t = this.model.get('type');
        this.model.set({
            type: 'multi',
            defaultType: t,
            value: undefined
        });
        itemSelector = new slicer.views.ItemSelectorWidget({
            parentView: this,
            el: dialogEl,
            rootPath: folder,
            root: folder,
            defaultSelectedResource: item,
            selectItem: true,
            showItems: true,
            model: this.model

        })
        itemSelector.once('g:saved', function() {
            itemSelector.$el.modal('hide');
        }).render();

    }

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        dialogEl = $('<div/>').appendTo('body');
        $('.modal').remove();

        transition = $.support.transition;
        $.support.transition = false;
        spyOn(slicer.views.ControlWidget.prototype, '_selectMultiFile').andCallFake(fakeselectMultiFile);

    });
    afterEach(function () {
        testEl.remove();
        dialogEl.remove();
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
                window.localStorage.setItem('girderToken', user.get('authToken').token);
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
            for (var i = 0; i < 20; i++) {
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
            return itemlist.length === 20;
        }, 'item creation');
    });

    it('test display of multifile', function () {
        var arg, item, w;
        runs(function () {
            w = new slicer.views.ControlWidget({
                parentView: null,
                rootPath: folder,
                el: testEl,
                model: new slicer.models.WidgetModel({
                    type: 'item',
                    title: 'Title',
                    id: 'item-widget'
                })
            });

            w.render();
            expect(w.$('.s-select-multifile-button').length).toBe(1);
            w.$('.s-select-multifile-button').click();

        });
        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 && $('.g-item-list-entry').length >0;
        }, 'the hierarchy widget to display');

        runs(function () {
            $('#g-input-element').val('[0-9][1-3]');
            $('#g-input-element').trigger('input');
        }, 'set regEx to [0-9][1-3]');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            var name_list = [];
            $('.g-selected .g-item-list-link').each( function(index, item) {
                name_list.push($(this)
                .clone()
                .children()
                .remove()
                .end()
                .text());
            });
            expect(name_list.includes("item#: 10")).toBe(false);
            expect(name_list.includes("item#: 11")).toBe(true);
            expect(name_list.includes("item#: 12")).toBe(true);
            expect(name_list.includes("item#: 13")).toBe(true);
            expect(name_list.includes("item#: 14")).toBe(false);
        }, 'testing for [0-9][1-3] regEx');

        runs(function () {
            $('#g-input-element').val(' [4-7]$');
            $('#g-input-element').trigger('input');
        }, 'set regEx to [0-9][1-3]');
        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            var name_list = [];
            $('.g-selected .g-item-list-link').each( function(index, item) {
                name_list.push($(this)
                .clone()
                .children()
                .remove()
                .end()
                .text());
            });
            expect(name_list.includes("item#: 4")).toBe(true);
            expect(name_list.includes("item#: 5")).toBe(true);
            expect(name_list.includes("item#: 6")).toBe(true);
            expect(name_list.includes("item#: 7")).toBe(true);
            expect(name_list.includes("item#: 14")).toBe(false);
            expect(name_list.includes("item#: 17")).toBe(false);
        }, 'Testing for End / [4-7]$/ regex');

        runs(function () {
            $('#g-input-element').val('');
            $('#g-input-element').trigger('input');
        }, 'set regEx to empty');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            expect($('.g-selected .g-item-list-link').length).toBe(21)
        }, 'Testing empty Regex value');

        runs(function () {
            $('#g-input-element').val('\\');
            $('#g-input-element').trigger('input');
        }, 'set regEx to error');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length == 0;
        });
        runs(function () {
            expect($('.g-validation-failed-message:visible').length).toBe(1)
        }, 'Testing empty Error Regex value');

        runs(function () {
            $('.g-submit-button').click();
            expect($('.g-validation-failed-message:visible').length).toBe(1)
        }, 'Attempting to Submit an invalid Regex');

        runs(function () {
            $('#g-input-element').val('');
            itemSelector._selectModel();
            itemSelector._hierarchyView.itemListView.trigger('g:changed');
        }, 'Testing resetting of the view and updating the list of items selected')

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        }, 'waiting for g:changed to be done');
        runs(function () {
            expect($('.g-selected .g-item-list-link').length).toBe(21)
        }, 'Testing result of g:changed');

        runs(function () {
            $('#g-input-element').val('[5]$');
            $('#g-input-element').trigger('input');
        }, 'set regEx to [5]');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });

        runs(function () {
            var name_list = [];
            $('.g-selected .g-item-list-link').each( function(index, item) {
                name_list.push($(this)
                .clone()
                .children()
                .remove()
                .end()
                .text());
            });
            expect(name_list.includes("item#: 5")).toBe(true);
            expect(name_list.includes("item#: 15")).toBe(true);
        }, 'Testing for End / [5]$/ regex');

        runs(function () {
            $('.g-submit-button').click();
        }, 'Attempting to Submit a valid Regex');

        waitsFor(function () {
            return $('.g-hierarchy-widget:visible').length === 0;
        }, 'the hierarchy widget to hide');


        runs(function () {
            expect(w.$('.form-control').val()).toBe('top level folder/RegEx([5]$)');
            expect(w.model.get('value').get('name')).toBe('[5]$');

        }, 'after submit clicked');

    });

});
