Open Questions for this document
================================

* Can Items take permissions from Groups and Folders, some combination?
* permission names, are these correct? No permission, Read-only, Edit, Admin
* does Edit permission allow a user to upload a new version of a resource?
* How do permissions work on Collections?
* Is the description of permissions on Folders correct?
* Is the description of permissions on Items correct?
* Is the description of permissions on Groups correct?
* Are there permissions on Users?


Areas to address in this document
=================================

* Group admin/management



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

A Girder ``Group`` is a collection of Girder ``Users``, with a common set of permissions and access to data.


Items
-----

A Girder ``Item`` is an atomic file (cannot be separated into smaller parts within Girder).  This could be a collection of files (or tar, zip, etc), but from Girder's persective it is considered an atomic file.  ``Items`` in Girder live in exactly one ``Folder``.  ``Items`` in Girder do not have permissions set on them, they inherit permissions by virtue of living in a ``Folder`` (which has permissions set on it) and by being included under the set of resources related to a ``Group``.

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

OPEN QUESTION: permission names

1) No permission (cannot view, edit, or delete a resource)
2) Read-only permission (can view and download resources)
3) Edit permission (includes Read-only permission, can edit metadata about the resource) OPEN QUESTION: upload new versions
4) Admin permission (includes Read-only and Edit permission, can delete the resource)

Permission Model
^^^^^^^^^^^^^^^^^

Permissions are resolved at the level of a ``User``, i.e., for any ``User``, an attempt to take a certain action will be allowed or disallowed based on the permissions for that ``User``, as a function of the resource, the operation, the permissions set on that resource for that ``User``, and the permissions set on that resource by any ``Groups`` the ``User`` is a member of.

Permissions are always additive.  That is, given a ``User`` with a certain permission on a resource, that permission can not be taken away from the ``User`` by addition of other permissions to the system, but only through removing existing permissions to that ``User`` or removing that ``User`` from a ``Group``.

Collections
^^^^^^^^^^^^^^^^^


TODO OPEN QUESTION: Perms on Collections

Folders
^^^^^^^^^^^^^^^^^


TODO OPEN QUESTION: Correct?

``Folders`` have permissions set on them at the individual ``User`` level.  ``Folders`` inherit permissions from their parent ``Folder`` and ultimately from a ``Collection``.
``Folders`` can also have permissions added to them by virtue of being included in a ``Group``.

Items
^^^^^^^^^^^^^^^^^


TODO OPEN QUESTION: Correct?

``Items`` always inherit their permissions from their parent ``Folder``. Each access-controlled resource (e.g. ``Folder``, ``Collection``) has a list of permissions granted on it, and each item in that list is a mapping of either ``Users`` to permission level or ``Groups`` to permission level.  This is best visualized by opening the "Access control" dialog on a ``Folder`` in the hierarchy. The actual permission level that a ``User`` has on that resource is defined as: the maximum permission level available based on the permissions granted to any ``Groups`` that the ``User`` is member of, or permissions granted to that ``User`` specifically.


Groups
^^^^^^^^^^^^^^^^^


TODO OPEN QUESTION: What are the permission levels on Groups? 

User
^^^^^^^^^^^^^^^^^

TODO OPEN QUESTION: are there some permissions on Users?  Can a user own or control another user with some permission?




Usage
========

Groups
------

TODO some stuff here, including invitations


which are the admin/moderator/member functions?

can invite user as member/moderator/admin
request invitation
invite
remove the invitation
accept invitation
accept invitation request
deny invitation request
leave group
join group
delete group
create a new group ? perm needed


add to group
remove from group

group member, moderator, admin, what can these do?


