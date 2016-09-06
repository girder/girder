(function () {
    var user, folder, subfolder, item, widget;

    describe('Test upload widget non-standard options', function () {
        it('create the widget', function () {
            runs(function () {
                $('body').off();

                new girder.views.widgets.UploadWidget({
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
                }).save();
            });

            waitsFor(function () {
                return !!item;
            }, 'item creation');
        });

        it('test custom hierarchy widget options', function () {
            runs(function () {
                $('body').off();

                widget = new girder.views.widgets.HierarchyWidget({
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
                return $('.g-hierarchy-widget').length > 0 &&
                       $('.g-folder-list-link').length > 0 &&
                       $('.g-item-list-link').length > 0;
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

                new girder.views.widgets.HierarchyWidget({
                    el: 'body',
                    parentModel: folder,
                    checkboxes: false,
                    parentView: null,
                    showItems: false
                });
            });

            waitsFor(function () {
                return $('.g-hierarchy-widget').length > 0 &&
                       $('.g-folder-list-link').length > 0;
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

    describe('Test access widget with non-standard options', function () {
        it('test non-modal rendering', function () {
            runs(function () {
                new girder.views.widgets.AccessWidget({
                    el: 'body',
                    modal: false,
                    model: folder,
                    modelType: 'folder',
                    parentView: null
                });
            });

            waitsFor(function () {
                return $('.g-public-container').length === 1;
            }, 'the access widget to render');

            runs(function () {
                expect($('#g-access-private').attr('checked')).toBe('checked');
                expect($('#g-access-public').attr('checked')).toBe(undefined);
                expect($('.g-save-access-list').length).toBe(1);
                expect($('.g-ac-list').length).toBe(1);
                expect($('.g-grant-access-container').length).toBe(1);
                expect($('.g-recursive-container .radio').length).toBe(2);
            });
        });

        it('test hiding elements', function () {
            runs(function () {
                $('body').empty().off();

                new girder.views.widgets.AccessWidget({
                    el: 'body',
                    modal: false,
                    model: folder,
                    modelType: 'folder',
                    hideRecurseOption: true,
                    hideSaveButton: true,
                    parentView: null
                });
            });

            waitsFor(function () {
                return $('.g-public-container').length === 1;
            }, 'the access widget to render');

            runs(function () {
                expect($('#g-access-private').attr('checked')).toBe('checked');
                expect($('#g-access-public').attr('checked')).toBe(undefined);
                expect($('.g-save-access-list').length).toBe(0);
                expect($('.g-ac-list').length).toBe(1);
                expect($('.g-grant-access-container').length).toBe(1);
                expect($('.g-recursive-container').length).toBe(0);
            });
        });
    });

    describe('Test search widget with non-standard options', function () {
        it('test fixed search mode', function () {
            runs(function () {
                $('body').empty().off();

                new girder.views.widgets.SearchFieldWidget({
                    el: 'body',
                    modes: 'prefix',
                    types: ['folder'],
                    parentView: null,
                    placeholder: 'test ph'
                }).render();

                expect($('input.g-search-field[placeholder="test ph"]').length).toBe(1);
                expect($('.g-search-mode-choose').length).toBe(0);

                $('.g-search-field').val('to').trigger('input');
            });

            waitsFor(function () {
                return $('.g-search-results').hasClass('open');
            }, 'prefix folder search to return');

            runs(function () {
                var results = $('li.g-search-result');
                expect(results.length).toBe(1);
                expect(results.find('a[resourcetype="folder"]').text()).toContain('top level folder');
            });
        });

        it('test multiple search modes', function () {
            runs(function () {
                $('body').empty().off();

                new girder.views.widgets.SearchFieldWidget({
                    el: 'body',
                    modes: ['text', 'prefix'],
                    types: ['folder'],
                    parentView: null
                }).render();

                expect($('.g-search-mode-choose').length).toBe(1);
                $('.g-search-field').val('to').trigger('input');
            });

            waitsFor(function () {
                return $('.g-search-results:visible').hasClass('open');
            }, 'folder text search to return');

            runs(function () {
                expect($('li.g-search-result').length).toBe(0);
                expect($('li.g-no-search-results.disabled').length).toBe(1);

                $('.g-search-mode-choose').click();
            });

            waitsFor(function () {
                return $('.popover-content:visible').length === 1;
            }, 'search mode select popover to appear');

            runs(function () {
                expect($('.popover-content p').text()).toContain('Choose search mode');
                expect($('.popover-content .radio').length).toBe(2);
                expect($('.popover-content .g-search-mode-radio[value="prefix"]:checked').length).toBe(0);
                expect($('.popover-content .g-search-mode-radio[value="text"]:checked').length).toBe(1);

                $('.popover-content .g-search-mode-radio[value="prefix"]').click();
            });

            waitsFor(function () {
                return $('li.g-search-result').length > 0;
            }, 'prefix search to be automatically run');

            runs(function () {
                expect($('li.g-search-result').text()).toContain('top level folder');
            });
        });
    });

    describe('Test metadata widget with non-standard options', function () {
        it('test editing custom field with custom callbacks', function () {
            var widget;
            var model = new girder.models.FolderModel({
                customMeta: {},
            });
            var addCbCalled = false;
            var editCbCalled = false;

            var addCb = function (key, value, success, err) {
                model.get('customMeta')[key] = value;
                addCbCalled = true;
                success();
            };
            var editCb = function (newKey, oldKey, value, success, err) {
                var meta = model.get('customMeta');
                delete meta[oldKey];
                meta[newKey] = value;
                editCbCalled = true;
                success();
            };

            runs(function () {
                widget = new girder.views.widgets.MetadataWidget({
                    el: 'body',
                    parentView: null,
                    item: model,
                    accessLevel: girder.constants.AccessType.WRITE,
                    onMetadataAdded: addCb,
                    onMetadataEdited: editCb,
                    fieldName: 'customMeta'
                });

                expect($('.g-widget-metadata-row').length).toBe(0);
                expect($('.g-widget-metadata-add-button').length).toBe(1);
                expect(addCbCalled).toBe(false);
                expect(editCbCalled).toBe(false);

                $('.g-widget-metadata-add-button').click();
            });

            waitsFor(function () {
                return $('.g-add-simple-metadata:visible').length > 0;
            }, 'metadata type dropdown to appear');

            runs(function () {
                // Save a metadata key, make sure add callback was called
                $('.g-add-simple-metadata').click();
                expect($('.g-widget-metadata-row').length).toBe(1);
                $('.g-widget-metadata-key-input').val('foo');
                $('.g-widget-metadata-value-input').val('bar');
                $('.g-widget-metadata-save-button').click();
                expect(addCbCalled).toBe(true);
                expect(editCbCalled).toBe(false);
                expect($('.g-widget-metadata-key-input').length).toBe(0);
                expect(_.keys(model.get('customMeta')).length).toBe(1);
                expect(model.get('customMeta').foo).toBe('bar');

                // Re-render the widget, make sure it displays properly
                widget.render();
                expect($('.g-widget-metadata-row').length).toBe(1);
                expect($('.g-widget-metadata-key').text()).toBe('foo');
                expect($('.g-widget-metadata-value').text()).toBe('bar');

                // Edit the existing field, make sure edit callback was called
                $('.g-widget-metadata-edit-button').click();
                $('.g-widget-metadata-value-input').val('baz');
                $('.g-widget-metadata-save-button').click();
                expect($('.g-widget-metadata-row').length).toBe(1);
                expect($('.g-widget-metadata-key').text()).toBe('foo');
                expect($('.g-widget-metadata-value').text()).toBe('baz');
            });
        });
    });
})();
