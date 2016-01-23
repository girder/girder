.. _web-client-event-catalog:

Web Client Event Catalog
========================

This provides a comprehensive set of Girder's web client events that may
be triggered by Girder core or any Girder core plugins. The name of each
event is listed, followed by the condition when it will be triggered.

.. _alphabetic-list-of-web-client-events:

Alphabetic List of Web Client Events
------------------------------------

* ``g:accessFetched`` - An access control list has been fetched from the server for an ``AccessControlledModel``, after calling ``fetchAccess`` on the model
* ``g:accessListSaved`` - An access control list has been saved to the server for an ``AccessControlledModel``, after calling ``updateAccess`` on the model
* ``g:adminAdded`` - An admin user has been added to a group
* ``g:alert`` - A brief alert should be displayed to the user, with some options including {icon, type, text, timeout}
* ``g:appload.after`` - The Girder web client application has been created
* ``g:appload.before`` - The Girder web client application is about to be created
* ``g:breadcrumbClicked`` - A breadcrumb link has been clicked in a ``HierarchyWidget``
* ``g:changed`` - The page of models (or a different page) in a collection has been fetched; In some cases a widget will trigger this event when its underlying collection has triggered the event, e.g. ``ItemListWidget`` and ``FolderListWidget``
* ``g:checkboxesChanged`` - The selected state of checkboxes in the ``FileListWidget`` or ``ItemListWidget`` have changed
* ``g:created`` - A new ``AssetstoreModel`` has been created by the ``NewAssetstoreWidget`` or when a new ``ThumbnailModel`` has been created by ``CreateThumbnailView`` in the thumbnails plugin
* ``g:deleted`` - A model has been deleted from the server, after calling ``destroy`` on a web client model
* ``g:demoted`` - A user model has been updated on the server such that the user has been demoted to ordinary member status in a group
* ``g:demoteUser`` - A user with admin privileges in a group clicks the UI control to demote a user in a group to ordinary member status
* ``g:error`` - An error is encountered generally, often by model methods
* ``g:event.`` - Prefix of events issued by notification ``EventStream``, e.g. creating a notification on the server of type='job_status' will issue ``g:event.job_status``
* ``g:event.job_status`` - Issued by notification ``EventStream`` when a server side event of type='job_status' is created
* ``g:fetched`` - A model has been fetched from the server, after calling ``fetch`` on the model; if an 'extraPath' option is sent to the model fetch method, then the ``g:fetched`` event will be suffixed with '.extraPath', e.g. ``this.model.fetch({extraPath: 'details'})`` and ``g:fetched.details`` in ``FolderInfoWidget``
* ``g:filesChanged`` - The user changes the file selection in the ``UploadWidget``
* ``g:fileUploaded`` - The ``MarkdownWidget`` has finished uploading a file, and then in turn by the ``EditFolderWidget``
* ``g:folderClicked`` - A folder link has been clicked on in the ``FolderListWidget``
* ``g:hide`` - The ``TaskProgressWidget`` has been hidden
* ``g:hierarchy.route`` - The ``HierarchyWidget`` has a route set, will pass the route set as '{route: route}'
* ``g:highlightItem`` - The route has been set to a global navigation view of 'Collections', 'Users', 'Groups'
* ``g:imported`` - An assetstore has been imported on the server
* ``g:invited`` - An invitiation has been sent to a user, to join a specific group
* ``g:inviteRequested`` - An invitation request has been created from a user to join a specific group
* ``g:itemClicked`` - A item link has been clicked on in the ``ItemListWidget``
* ``g:jobClicked`` - A job link has been clicked on in the ``JobListWidget``
* ``g:joined`` - A user has joined a group
* ``g:login`` - The currently logged in user in the UI has changed, due to a user logging in, logging out, or registering a new user
* ``g:login-changed`` - A valid temporary token has granted access to a user
* ``g:login.error`` - A user attempted to log in, but encountered an error
* ``g:login.success`` - A user has successfully logged in
* ``g:loginUi`` - The login link has been clicked on in the UI
* ``g:logout.error`` - An error was encountered when a user tried to logout
* ``g:logout.success`` - A user has successfully logged out
* ``g:moderatorAdded`` - A user has been made a moderator of a group, either through promotion from member or demotion from admin
* ``g:navigateTo`` - A view passed with the event should be displayed in the g-app-body-container part of the main Girder layout
* ``g:passwordChanged`` - A user's password has changed, either by the user or a site admin
* ``g:promoted`` - A user has been promoted to a moderator or admin on a group
* ``g:quotaPolicyFetched`` - A quota policy has been fetched from the server, in the user_quota plugin
* ``g:quotaPolicySaved`` - A quota policy has been saved on the server, in the user_quota plugin
* ``g:registerUi`` - The register link has been clicked on in the UI
* ``g:removed`` - All relations between a user and a group have been severed, including membership, invitations, or membership requests
* ``g:removeMember`` - The removal of a user from a group has been requested in the UI
* ``g:rendered`` - The ``ItemView`` has finished rendering, specifically after the ``FileListWidget`` has fetched its collection
* ``g:resetPasswordUi`` - The reset password link has been clicked on in the UI
* ``g:resultClicked`` - A particular search result has been clicked in the ``SearchFieldWidget``
* ``g:saved`` - A model has been saved on the server, after calling ``save`` on a web client model
* ``g:sendInvite`` - An invitation for a user to join a group has been requested in the UI
* ``g:upload.chunkSent`` - Called on each chunk of an upload sent
* ``g:upload.complete`` - The upload of an individual file is complete
* ``g:upload.error`` - An upload fails partway through sending data
* ``g:upload.errorStarting`` - An upload fails to start
* ``g:uploadFinished`` - All files have been successfully uploaded by the ``UploadWidget``
* ``g:upload.progress`` - Called regularly with progress updates on uploads
* ``g:uploadStarted`` - A user has clicked on Start Upload in the ``UploadWidget``

.. _functionally-grouped-web-client-events:

Functionally Grouped Web Client Events
--------------------------------------

General Application Events
^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``g:alert`` - A brief alert should be displayed to the user, with some options including {icon, type, text, timeout}
* ``g:appload.after`` - The Girder web client application has been created
* ``g:appload.before`` - The Girder web client application is about to be created
* ``g:changed`` - The page of models (or a different page) in a collection has been fetched; In some cases a widget will trigger this event when its underlying collection has triggered the event, e.g. ``ItemListWidget`` and ``FolderListWidget``

Group Events
^^^^^^^^^^^^

* ``g:adminAdded`` - An admin user has been added to a group
* ``g:demoted`` - A user model has been updated on the server such that the user has been demoted to ordinary member status in a group
* ``g:demoteUser`` - A user with admin privileges in a group clicks the UI control to demote a user in a group to ordinary member status
* ``g:invited`` - An invitiation has been sent to a user, to join a specific group
* ``g:inviteRequested`` - An invitation request has been created from a user to join a specific group
* ``g:joined`` - A user has joined a group
* ``g:moderatorAdded`` - A user has been made a moderator of a group, either through promotion from member or demotion from admin
* ``g:promoted`` - A user has been promoted to a moderator or admin on a group
* ``g:removed`` - All relations between a user and a group have been severed, including membership, invitations, or membership requests
* ``g:removeMember`` - The removal of a user from a group has been requested in the UI
* ``g:sendInvite`` - An invitation for a user to join a group has been requested in the UI

Model Events
^^^^^^^^^^^^

* ``g:accessFetched`` - An access control list has been fetched from the server for an ``AccessControlledModel``, after calling ``fetchAccess`` on the model
* ``g:accessListSaved`` - An access control list has been saved to the server for an ``AccessControlledModel``, after calling ``updateAccess`` on the model
* ``g:deleted`` - A model has been deleted from the server, after calling ``destroy`` on a web client model
* ``g:error`` - An error is encountered generally, often by model methods
* ``g:fetched`` - A model has been fetched from the server, after calling ``fetch`` on the model; if an 'extraPath' option is sent to the model fetch method, then the ``g:fetched`` event will be suffixed with '.extraPath', e.g. ``this.model.fetch({extraPath: 'details'})`` and ``g:fetched.details`` in ``FolderInfoWidget``
* ``g:saved`` - A model has been saved on the server, after calling ``save`` on a web client model


``UploadWidget`` and ``FileModel`` Events
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more information on the ``UploadWidget`` and ``FileModel`` see the developer cookbook section :ref:`Upload a file<upload-a-file>`.

* ``g:filesChanged`` - The user changes the file selection in the ``UploadWidget``
* ``g:upload.chunkSent`` - Called on each chunk of an upload sent
* ``g:upload.complete`` - The upload of an individual file is complete
* ``g:upload.error`` - An upload fails partway through sending data
* ``g:upload.errorStarting`` - An upload fails to start
* ``g:uploadFinished`` - All files have been successfully uploaded by the ``UploadWidget``
* ``g:upload.progress`` - Called regularly with progress updates on uploads
* ``g:uploadStarted`` - A user has clicked on Start Upload in the ``UploadWidget``

User Session Events
^^^^^^^^^^^^^^^^^^^

* ``g:login`` - The currently logged in user in the UI has changed, due to a user logging in, logging out, or registering a new user
* ``g:login-changed`` - A valid temporary token has granted access to a user
* ``g:login.error`` - A user attempted to log in, but encountered an error
* ``g:login.success`` - A user has successfully logged in
* ``g:loginUi`` - The login link has been clicked on in the UI
* ``g:logout.error`` - An error was encountered when a user tried to logout
* ``g:logout.success`` - A user has successfully logged out
