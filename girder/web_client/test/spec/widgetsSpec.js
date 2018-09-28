girderTest.startApp();

function _setProgress(test, duration, resourceId, resourceName) {
    /* Set or update a current progress notification.
     *
     * :param test: test parameter to send to the webclienttest/progress
     *     endpoint
     * :param duration: duration to send to the endpoint
     * :param resourceId: optional resource ID that the progress notification
     *     is associated with.
     * : param resourceName: optional resource type that the progress notification
     *     is associated with.
     */
    girder.rest.restRequest({
        url: 'webclienttest/progress',
        method: 'GET',
        data: {
            test: test,
            duration: duration,
            resourceId: resourceId,
            resourceName: resourceName
        }
    });
}

describe('Test widgets that are not covered elsewhere', function () {
    it('register a user',
        girderTest.createUser('admin',
            'admin@email.com',
            'Admin',
            'Admin',
            'adminpassword!'));

    it('test task progress widget', function () {
        runs(function () {
            expect($('#g-app-progress-container:visible').length).toBe(0);
            _setProgress('success', 0, null, null);
        });
        waitsFor(function () {
            return $('.g-task-progress-title').text() === 'Progress Test';
        }, 'progress to be shown');
        waitsFor(function () {
            return $('.g-task-progress-message').text() === 'Done';
        }, 'progress to be complete');

        runs(function () {
            _setProgress('error', 0, null, null);
        });
        waitsFor(function () {
            return $('.g-task-progress-title:last').text() === 'Progress Test';
        }, 'progress to be shown');
        waitsFor(function () {
            return $('.g-task-progress-message:last').text() === 'Error: Progress error test.';
        }, 'progress to report an error');

        var onErrorEvent;
        var onProgressEvent;
        runs(function () {
            onErrorEvent = jasmine.createSpy('onErrorEvent');
            girder.utilities.eventStream.on('g:error', onErrorEvent);
            onProgressEvent = jasmine.createSpy('onErrorEvent');
            girder.utilities.eventStream.on('g:event.progress', onProgressEvent);
        }, 'setup EventStream event testing');

        runs(function () {
            onProgressEvent.reset();
            onErrorEvent.reset();

            _setProgress('success', 0, null, null);
        }, 'cause a progress notification');
        waitsFor(function () {
            return onProgressEvent.wasCalled;
        }, 'progress event to be triggered');
        runs(function () {
            expect(onErrorEvent).not.toHaveBeenCalled();
        });

        runs(function () {
            onProgressEvent.reset();
            onErrorEvent.reset();

            _setProgress('error', 0, null, null);
        }, 'cause an error notification');
        waitsFor(function () {
            return onProgressEvent.wasCalled;
        }, 'progress event to be triggered');
        runs(function () {
            expect(onErrorEvent).not.toHaveBeenCalled();
        });

        runs(function () {
            /* Create a progress notification related to a specific resource */
            _setProgress('success', 0, 'some_folder_id', 'folder');
        });

        waitsFor(function () {
            /* Make sure the progress notification links to that resource */
            return $('.g-task-progress-title:last a').attr('href') === '#folder/some_folder_id';
        }, 'progress for a folder to be shown');

        runs(function () {
            /* Ask for a long test, so that on slow machines we can still
             * detect a partial progress. */
            _setProgress('success', 100, null, null);
        });
        waitsFor(function () {
            return $('.g-task-progress-message:last').text() === 'Progress Message';
        }, 'progress to be shown');
        runs(function () {
            expect($('.g-progress-widget-container').length > 0);
        });
        waitsFor(function () {
            /* Wait until at least 4% has progressed, as it makes our
             * subsequent test not require an explicit wait */
            return parseFloat($('.progress-status .progress-percent:last').text()) >= 4 &&
              /left$/.test($('.progress-status .progress-left:last').text());
        }, 'progress to show estimated time');

        /* There is a 5 second timeout for fading out the success message.  We
         * wait for 4% of the progress of the previous task, there should be
         * less than a second left to wait for the two previous success
         * messages to vanish (but the error message might still be around). */
        waitsFor(function () {
            return $('.g-progress-widget-container').length < 5;
        }, 'at least the first progress to be hidden');

        runs(function () {
            girder.utilities.eventStream.close();
        }, 'close the EventStream');
        waitsFor(function () {
            return $('.g-progress-widget-container').length === 0;
        }, 'Progress to clear.');

        runs(function () {
            girder.utilities.eventStream.open();
            girder.rest.restRequest({
                url: 'webclienttest/progress/stop',
                method: 'PUT',
                async: false
            });

            girder.utilities.eventStream.off('g:error', onErrorEvent);
            girder.utilities.eventStream.off('g:event.progress', onProgressEvent);
        }, 'clean up testing changes');
    });
});

describe('Test folder info widget async fetch', function () {
    var folders = new girder.collections.FolderCollection();

    it('fetch the current user\'s folders', function () {
        runs(function () {
            expect(girder.auth.getCurrentUser()).not.toBe(null);
            folders.fetch({
                parentType: 'user',
                parentId: girder.auth.getCurrentUser().id
            });
        });

        waitsFor(function () {
            return folders.models.length > 0;
        }, 'child folders to be fetched');
    });

    it('show a folder info widget for one of the folders', function () {
        folders.models[0].set('description', 'hello world');

        var widget = new girder.views.widgets.FolderInfoWidget({
            el: $('#g-dialog-container'),
            model: folders.models[0],
            parentView: null
        });

        waitsFor(function () {
            return $('.modal-body .g-folder-description').text().indexOf('hello world') !== -1;
        }, 'details to be fetched and the widget to render');
        girderTest.waitForDialog();

        runs(function () {
            expect($('.g-folder-info-line[property="nItems"]').text()).toBe(
                'Contains 0 items totaling 0 B');
            expect($('.g-folder-info-line[property="nFolders"]').text()).toBe(
                'Contains 0 subfolders');
            expect($('.g-folder-info-line[property="id"]:contains("' + widget.model.id +
                '")').length).toBe(1);
        });
    });
});
