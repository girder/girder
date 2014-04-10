Girder User's Guide
===================

Girder is a Data Management Toolkit.  It is a complete back-end (server side) technology that can be used with other applications via its RESTful API, or it can be used via its own front-end (client side web pages and JavaScript).

Our aims for Girder is for it to be robust, performant, extensible, and grokable. 

Girder is built in Python.

Girder is open source, licensed under the Apache 2.0 license.

Document Conventions
====================

This document is written for end-users of Girder, rather than developers.  Since it was written by developers, sometimes we fail at making this distinction, please remind (and forgive) us.

Girder specific entities will be ``formatted like this``.

Concepts
========

Users
-----

This is a common software concept, isn't it nice that we didn't change its established meaning!  Each user of Girder should have a ``User`` created within Girder.  Their Girder ``User`` will determine their permissions and can store and share their data.

Groups
-----

``Groups`` group together ``Users``; the most common usage example would be to give access to specific resources to any member of a ``Group``.



Items
-----

A Girder ``Item`` is an atomic file (cannot be separated into smaller parts within Girder).  This could be a collection of files (or tar, zip, etc), but from Girder's persective it is considered an atomic file.  ``Items`` in Girder live in exactly one ``Folder``.  ``Items`` in Girder do not have permissions set on them, they inherit permissions by virtue of living in a ``Folder`` (which has permissions set on it).

Folders
-------

A Girder ``Folder`` is the common software concept of a folder, namely a hierarchically nested organizational structure.  Girder ``Folders`` can contain nothing (although this may not be particularly useful), other ``Folders``, ``Items``, or a combination of ``Folders`` and ``Items``. ``Folders`` in Girder have permissions set on them, and the ``Items`` within them inherit permissions from their containing ``Folders``.

Collections
-----------

A Girder ``Collection`` is functional top level grouping of ``Folders``.  A ``Collection`` collects resources (``Folders``, ``Items``, and ``Users``) that should have some common usage, e.g. for a particular project.

Permissions
-----------

Permission Levels
^^^^^^^^^^^^^^^^^

There are four levels of permission a ``User`` can have on a resource, these levels are in a strict hierarchy with a higher permission level including all of the permissions below it.


1) No permission (cannot view, edit, or delete a resource)
2) ``READ`` permission (can view and download resources)
3) ``WRITE`` permission (includes ``READ`` permission, can edit metadata about the resource)
4) ``ADMIN`` permission (includes ``READ`` and ``WRITE`` permission, can delete the resource)

A site admin always has permission to take any action.


Permission Model
^^^^^^^^^^^^^^^^^

Permissions are resolved at the level of a ``User``, i.e., for any ``User``, an attempt to take a certain action will be allowed or disallowed based on the permissions for that ``User``, as a function of the resource, the operation, the permissions set on that resource for that ``User``, and the permissions set on that resource by any ``Groups`` the ``User`` is a member of.

Permissions are always additive.  That is, given a ``User`` with a certain permission on a resource, that permission can not be taken away from the ``User`` by addition of other permissions to the system, but only through removing existing permissions to that ``User`` or removing that ``User`` from a ``Group``.  Once again, a site admin always has permission to take any action.


Collections
^^^^^^^^^^^^^^^^^

``Collections`` can be ``Public`` (meaning viewable even by anonymous users) or ``Private`` (meaning viewable only by those with ``READ`` access).  ``Collections`` can have permissions set on them at the individual ``User`` level and ``Group`` level, meaning that a given ``User`` or ``Group`` can have ``READ``, ``WRITE``, or ``ADMIN`` permissions set on the ``Collection``.


Folders
^^^^^^^^^^^^^^^^^

``Folders`` can be ``Public`` (meaning viewable even by anonymous users) or ``Private`` (meaning viewable only by those with ``READ`` access).  ``Folders`` can have permissions set on them at the individual ``User`` level and ``Group`` level, meaning that a given ``User`` or ``Group`` can have ``READ``, ``WRITE``, or ``ADMIN`` permissions set on the ``Folder``.  ``Folders`` inherit permissions from their parent ``Folder``.

Items
^^^^^^^^^^^^^^^^^

``Items`` always inherit their permissions from their parent ``Folder``. Each access-controlled resource (e.g. ``Folder``, ``Collection``) has a list of permissions granted on it, and each item in that list is a mapping of either ``Users`` to permission level or ``Groups`` to permission level.  This is best visualized by opening the "Access control" dialog on a ``Folder`` in the hierarchy. The actual permission level that a ``User`` has on that resource is defined as: the maximum permission level available based on the permissions granted to any ``Groups`` that the ``User`` is member of, or permissions granted to that ``User`` specifically.


Groups
^^^^^^^^^^^^^^^^^

For access control, ``Groups`` can be given any level of access to a resource that an individual ``User`` can, and this is managed at the level of the resource in question.  

For permissions on ``Groups`` themselves, ``Public`` Groups are viewable (``READ`` permission) to anyone, even anonymous users.  ``Private`` ``Groups`` are not viewable or even listable to any ``Users`` except those that are members of the ``Group``, or those that have been invited to the ``Group``.  

``Groups`` have three levels of roles that ``Users`` can have within the ``Group``.  They can be ``Members``, ``Moderators`` (also indicates that they are ``Members``), and ``Administrators`` (also indicates that they are ``Members``).

``Users`` that are not ``Members`` of a group can request to become ``Members`` of a ``Group`` if that ``Group`` is ``Public``.

``Members`` of a ``Group`` can see the membership list of the ``Group``, including roles, and can see pending requests and invitations for the group.  If a ``User`` has been invited to a ``Group``, they have ``Member`` access to the ``Group`` even before they have accepted the invitation.  A ``Member`` of a ``Group`` can leave the group, at which point they are no longer ``Members`` of the ``Group``.

``Moderators`` of a ``Group`` have all of the abilities of ``Group`` ``Members``.  ``Moderators`` can also invite ``Users`` to become ``Members``, can accept or reject a request by a ``User`` to become a ``Member``, can remove ``Members`` or ``Moderators`` from the ``Group``, and can edit the ``Group`` which includes changing the name and description and changing the ``Public``/``Private`` status of the ``Group``. 

``Administrators`` of a ``Group`` have all of the abilities of ``Group`` ``Moderators``.  ``Administrators`` can also delete the ``Group``, promote a ``Member`` to ``Moderator`` or ``Administrator``, demote an ``Administrator`` or ``Moderator`` to ``Member``, and remove any ``Member``, ``Moderator``, or ``Administrator`` from the ``Group``.

The creator of a ``Group`` is an ``Administrator`` of a group.  Any logged in ``User`` can create a ``Group``.  


User
^^^^^^^^^^^^^^^^^

`Users` have ``ADMIN`` access on themselves, and have ``READ`` access on other `Users`.

Usage
========

Clients
========

jQuery Plugins
--------------

.. js:function:: $.girderBrowser(cfg)

    :param object cfg: Configuration object

    :param boolean caret: Draw a caret on main menu to indicate dropdown (`true` by
        default).

    :param string label: The text to display in the main menu dropdown.

    :param string api: The root path to the Girder API (`/api/v1` by default).

    :param function(item,api) selectItem: A function to call when an item is
        clicked.  It will be passed the item's information and the API root.

    :param function(folder,api) selectFolder: A function to call when a folder
        is clicked.  It will be passed the folder's information and the API root.

    :param boolean search: Include a search box for gathering general string
        search results.

    :param function(result,api) selectSearchResult: A function to call when a
        search result is clicked.  It will be passed the result item's information
        and the API root.

This plugin creates a Bootsrap dropdown menu reflecting the current contents of
a Girder server as accessible by the logged-in user.  The selection on which
this plugin is invoked should be an ``<li>`` element that is part of a Bootstrap
navbar.  For example:

.. code-block:: html

    <div class="navbar navbar-default navbar-fixed-top">
        <div class=navbar-header>
            <a class=navbar-brand href=/examples>Girder</a>
        </div>

        <ul class="nav navbar-nav">
            <li id=girder-browser>
                <a>Dummy</a>
            </li>
        </ul>
    </div>

Then, in a JavaScript file:

.. code-block:: javascript

    $("#girder-browser").girderBrowser({
        // Config options here
        //     .
        //     .
        //     .
    });

The anchor text "dummy" in the example HTML will appear in the rendered page if
the plugin fails to execute for any reason.  This is purely a debugging measure
- since the plugin empties the target element before it creates the menu, the
anchor tag (or any other content) is not required.
