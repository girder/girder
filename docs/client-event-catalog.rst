Client Event Catalog
====================

This provides a comprehensive set of Girder's web client events that may
be triggered by Girder core or any Girder core plugins. The name of each
event is listed, followed by the condition when it will be triggered.

Alphabetic List of Client Events
--------------------------------

* 'g:accessFetched' - An access control list has been fetched from the server for an AccessControlledModel
* 'g:accessListSaved' - An access control list has been saved to the server for an AccessControlledModel
* 'g:adminAdded' - An admin user has been added to a group
* 'g:alert' - A brief alert should be displayed to the user, with some options including {icon, type, text, timeout}
* 'g:appload.after' - The Girder web client application has been created
* 'g:appload.before' - The Girder web client application is about to be created
* 'g:breadcrumbClicked' - A breadcrumb link has been clicked in a HierarchyWidget
* 'g:changed' - When the page of models (or a different page) in a Collection has been fetched; In some cases a widget will trigger this event when its underlying collection has triggered the event, e.g. ItemListWidget and FolderListWidget
* 'g:checkboxesChanged' - When the selected state of checkboxes in the FileListWidget or ItemListWidget have changed
* 'g:created' - When a new AssetstoreModel has been created by the NewAssetstoreWidget or when a new ThumbnailModel has been created by CreateThumbnailView in the thumbnails plugin
* 'g:deleted'
* 'g:demoted'
* 'g:demoteUser'
* 'g:error'
* 'g:event.job_status'
* 'g:fetched'
* 'g:filesChanged'
* 'g:fileUploaded'
* 'g:folderClicked'
* 'g:hide'
* 'g:hierarchy.route'
* 'g:highlightItem'
* 'g:imported'
* 'g:invited'
* 'g:inviteRequested'
* 'g:itemClicked'
* 'g:jobClicked'
* 'g:joined'
* 'g:login'
* 'g:login-changed'
* 'g:login.error'
* 'g:login.success'
* 'g:loginUi'
* 'g:logout.error'
* 'g:logout.success'
* 'g:moderatorAdded'
* 'g:navigateTo'
* 'g:passwordChanged'
* 'g:promoted'
* 'g:quotaPolicyFetched'
* 'g:quotaPolicySaved'
* 'g:registerUi'
* 'g:removed'
* 'g:removeMember'
* 'g:rendered'
* 'g:resetPasswordUi'
* 'g:resultClicked'
* 'g:saved'
* 'g:sendInvite'
* 'g:upload.chunkSent'
* 'g:upload.complete'
* 'g:upload.error'
* 'g:upload.errorStarting'
* 'g:uploadFinished'
* 'g:upload.progress'
* 'g:uploadStarted'

TODO: not sure what to do here yet

* ??src/utilities/EventStream.js:41:                stream.trigger('g:event.' + obj.type, obj);

Functionally Grouped Client Events
----------------------------------

General Application Events
^^^^^^^^^^^^^^^^^^^^^^^^^^

* 'g:alert' - When a brief alert should be displayed to the user, with some options including {icon, type, text, timeout}
* 'g:appload.after' - The Girder web client application has been created
* 'g:appload.before' - The Girder web client application is about to be created
* 'g:changed' - When the page of models (or a different page) in a Collection has been fetched; In some cases a widget will trigger this event when its underlying collection has triggered the event, e.g. ItemListWidget and FolderListWidget

Group Events
^^^^^^^^^^^^

* 'g:adminAdded' - An admin user has been added to a group
