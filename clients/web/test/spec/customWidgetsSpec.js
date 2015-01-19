
describe('Test upload widget non-standard options', function () {
    it('create the widget', function () {
        runs(function () {
            $('body').off();

            new girder.views.UploadWidget({
                noParent: true,
                modal: false,
                title: null,
                el: 'body',
                parentView: null
            }).render();

            expect($('.modal').length).toBe(0);
            expect($('#g-upload-form h4').length).toBe(0);
            expect($('.g-dialog-subtitle').length).toBe(0);
            expect($('.g-drop-zone:visible').length).toBe(1);
            expect($('.g-start-upload.btn.disabled:visible').length).toBe(1);
            expect($('.g-overall-progress-message').text()).toBe('No files selected');
        });
    });
});

describe('Test hierarchy widget non-standard options', function () {
    var user, folder, subfolder, item, widget;

    it('register a user', function () {
        runs(function () {
            var _user = new girder.models.UserModel({
                login: 'mylogin',
                password:'mypassword',
                email: 'email@email.com',
                firstName: 'First',
                lastName: 'Last'
            }).on('g:saved', function () {
                user = _user;
            }).save();
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
            }).save();
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
            }).save();
        });

        waitsFor(function () {
            return !!folder;
        }, 'subfolder creation');
    });

    it('create item', function () {
        runs(function () {
            var _item = new girder.models.ItemModel({
                folderId: folder.get('_id'),
                name: 'an item'
            }).on('g:saved', function () {
                item = _item;
            }).save();
        });

        waitsFor(function () {
            return !!item;
        }, 'item creation');
    });

    it('test custom hierarchy widget options', function () {
        runs(function () {
            $('body').off();

            widget = new girder.views.HierarchyWidget({
                el: 'body',
                parentModel: folder,
                onItemClick: function (item) {
                    widget.selectItem(item);
                },
                showActions: false,
                parentView: null
            });
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            expect($('.g-upload-here-button').length).toBe(0);
            expect($('.g-hierarchy-actions-header').length).toBe(0);
            expect($('.g-list-checkbox').length).toBe(2);
            expect($('.g-select-all').length).toBe(0);
            expect($('.g-folder-list-link').text()).toBe('subfolder');
            expect($('.g-item-list-link').text()).toBe('an item');
            expect(widget.getSelectedItem()).toBe(null);

            $('.g-item-list-link').click();
        });

        waitsFor(function () {
            var selected = widget.getSelectedItem();
            return selected && selected.get('_id') === item.get('_id');
        }, 'item to be selected');

        runs(function () {
            expect($('.g-item-list-entry.g-selected').length).toBe(1);

            $('body').empty().off();

            new girder.views.HierarchyWidget({
                el: 'body',
                parentModel: folder,
                checkboxes: false,
                parentView: null,
                showItems: false
            });
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0;
        }, 'the hierarchy widget with no checkboxes to display');

        runs(function () {
            expect($('.g-upload-here-button').length).toBe(1);
            expect($('.g-hierarchy-actions-header').length).toBe(1);
            expect($('.g-list-checkbox').length).toBe(0);
            expect($('.g-select-all').length).toBe(0);
            expect($('.g-checked-actions-buttons').length).toBe(0);
            expect($('.g-folder-list-link').text()).toBe('subfolder');
            expect($('.g-item-list-link').length).toBe(0);
        });
    });
});
