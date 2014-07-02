Girder User's Guide
*******************

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

A Girder ``Item`` can contain any number of arbitrary key/value pairs, termed metadata.  Metadata keys must be strings and must never contain a period ('.') or begin with a dollar sign ('$').  Metadata values can be anything, including strings, numeric values, and even arbitrary JSON objects.

Files
-----

``Files`` represent discrete data objects known to Girder. ``Files`` exist within ``Items``, typically with a
one-to-one relationship between the ``File`` and its containing ``Item``. ``Files`` in Girder are much like
files on a filesystem, but they are actually more abstract. For instance, some ``Files`` are simply links
to external URLs. All ``Files`` that are not external links must be contained within an ``Assetstore``.


.. _assetstores:

Assetstores
-----------

``Assetstores`` are an abstraction representing a repository where the bytes of ``Files`` are
actually stored. The ``Assetstores`` known to a Girder instance may only be set up and
managed by administrator ``Users``.

In the core of Girder, there are three supported ``Assetstore`` types:

* **Filesystem**

Files uploaded into this type of ``Assetstore`` will be stored on the local system
filesystem of the server using content-addressed storage. Simply specify the root
directory under which files should be stored.

.. note:: If your Girder environment has multiple different application servers
   and you plan to use the Filesystem assetstore type, you must set the assetstore
   root to a location on the filesystem that is shared between all of the application
   servers.

* **GridFS**

This ``Assetstore`` type stores files directly within your Mongo database using
the GridFS model. You must specify the database name where files will be stored;
for now, the same credentials will be used for this database as for the main
application database.

This database type has the advantage of automatically scaling horizontally with
your DBMS. However, it is marginally slower than the Filesystem assetstore type
in a typical single-server use case.

* **S3**

This ``Assetstore`` type stores files in an Amazon S3 bucket. You must provide
the bucket name, an optional path prefix within the bucket, and authentication
credentials for the bucket. When using this assetstore type, Girder acts as the
broker for the data within S3 by authorizing the user agent via signed HTTP requests.
The primary advantage of this type of assetstore is that none of the actual bytes
of data being uploaded and downloaded ever go through the Girder system, but instead
are sent directly between the client and S3.

If you want to use an S3 assetstore, the bucket used must support CORS requests.
This can be edited by navigating to the bucket in the AWS S3 console, selecting
**Properties**, then **Permissions**, and then clicking **Edit CORS Configuration**.
The below CORS configuration is sufficient for Girder's needs. ::

    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <CORSRule>
            <AllowedOrigin>*</AllowedOrigin>
            <AllowedMethod>GET</AllowedMethod>
            <AllowedMethod>PUT</AllowedMethod>
            <AllowedMethod>POST</AllowedMethod>
            <MaxAgeSeconds>3000</MaxAgeSeconds>
            <ExposeHeader>ETag</ExposeHeader>
            <AllowedHeader>*</AllowedHeader>
        </CORSRule>
    </CORSConfiguration>


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
