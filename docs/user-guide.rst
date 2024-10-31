User Guide
**********

Girder is a Data Management Toolkit.  It is a complete back-end (server side)
technology that can be used with other applications via its RESTful API, or it
can be used via its own front-end (client side web pages and JavaScript).

Girder is designed to be robust, fast, scalable, extensible, and easy to understand.

Girder is built in Python.

Girder is open source, licensed under the `Apache License, Version 2.0 <http://www.apache.org/licenses/LICENSE-2.0.html>`_.

Document Conventions
====================

This User Guide is written for end-users of Girder, rather than developers. If you
have suggestions or questions about this documentation, feel free to contact us through our
`Github Discussions forum <https://github.com/orgs/girder/discussions>`_,
`on GitHub <https://github.com/girder/girder>`_, or `through Kitware support <mailto:kitware@kitware.com>`_.

Girder specific entities will be ``formatted like this``.

.. _concepts:

Concepts
========

Users
-----

Like in many systems, ``Users`` in Girder correspond to the identity of a user
of the system. It is possible to use many features of Girder anonymously (that is,
without being logged in as a registered user), but typically in order to make
changes to the system, a user must be logged in as their corresponding ``User``
account. ``Users`` can be granted permissions on resources in the system directly,
and can belong to ``Groups``.

Groups
------

``Groups`` group together ``Users``. ``Users`` can belong to any number of ``Groups``,
and usually join by being invited and accepting the invitation. One of the main
purposes of ``Groups`` is to allow role-based access control; resources can grant access to
``Groups`` rather than just individual users, such that changing access to sets of resources
can be managed simply by changing ``Group`` membership. See the :ref:`permissions`
section for more information about group-based access control.

Collections
-----------

``Collections`` are the top level objects in the data organization hierarchy.
Within each ``Collection``, there can be many ``Folders``, and the ``Collection``
itself is also an access controlled resource. Typically ``Collections`` are used
to group data that share something in common, such as what project the data are
used for, or what institution they belong to.

Folders
-------

A Girder ``Folder`` is the common software concept of a folder, namely a
hierarchically nested organizational structure.  Girder ``Folders`` can contain
nothing (although this may not be particularly useful), other ``Folders``,
``Items``, or a combination of ``Folders`` and ``Items``. ``Folders`` in Girder
have permissions set on them, and the ``Items`` within them inherit permissions
from their containing ``Folders``.

Items
-----

A Girder ``Item`` is the basic unit of data in the system. ``Items`` live beneath
``Folders`` and contain 0 or more ``Files``. ``Items`` in Girder do not have permissions set
on them, they inherit permissions by virtue of living in a ``Folder`` (which has
permissions set on it). Most ``Items`` contain a single ``File``, except
in special cases where multiple files make up a single piece of data.

Each ``Item`` may contain any number of arbitrary key/value pairs, termed
metadata.  Metadata keys must be non-empty strings and must not contain a period ('.')
or begin with a dollar sign ('$').  Metadata values can be anything, including
strings, numeric values, and even arbitrary JSON objects.

Files
-----

``Files`` represent raw data objects, just like the typical concept of files in
a filesystem. ``Files`` exist within ``Items``, typically with a one-to-one relationship
between the ``File`` and its containing ``Item``. ``Files`` in Girder are much like files on
a filesystem, but they are actually more abstract. For instance, some ``Files``
are simply links to external URLs. All ``Files`` that are not external links
must be contained within an ``Assetstore``.

.. _assetstores:

Assetstores
-----------

``Assetstores`` are an abstraction representing a repository where the raw bytes of
``Files`` are actually stored. The ``Assetstores`` known to a Girder instance
may only be set up and managed by administrator ``Users``.

In the core of Girder, there are three supported ``Assetstore`` types:

Filesystem
^^^^^^^^^^

Files uploaded into this type of ``Assetstore`` will be stored on the local
system filesystem of the server using content-addressed storage. Simply specify
the root directory under which files should be stored.

.. note:: If your Girder environment has multiple different application servers
   and you plan to use the Filesystem assetstore type, you must set the
   assetstore root to a location on the filesystem that is shared between all
   of the application servers.

S3
^^

This ``Assetstore`` type stores files in an **Amazon S3** bucket. You must
provide the bucket name, an optional path prefix within the bucket, and
authentication credentials for the bucket. When using this assetstore type,
Girder acts as the broker for the data within S3 by authorizing the user agent
via signed HTTP requests. The primary advantage of this type of assetstore is
that none of the actual bytes of data being uploaded and downloaded ever go
through the Girder system, but instead are sent directly between the client and
S3.

If you want to use an S3 assetstore, the bucket used must support CORS requests.
This can be edited by navigating to the bucket in the AWS S3 console, selecting
**Properties**, then **Permissions**, and then clicking **Edit CORS Configuration**.
The below CORS configuration is sufficient for Girder's needs:

.. code-block:: json

    [
        {
            "AllowedHeaders": [
                "*"
            ],
            "AllowedMethods": [
                "GET",
                "PUT",
                "POST"
            ],
            "AllowedOrigins": [
                "*"
            ],
            "ExposeHeaders": [
                "ETag"
            ],
            "MaxAgeSeconds": 3000
        }
    ]

.. note::

    Google Storage is supported through an S3 assetstore.  Specify the service as ``storage.googleapis.com``.  Public storage buckets can be accessed in read-only mode without an access key ID or secret access key.

    Support for Google Storage may not be complete, as it is accessed via an S3 access library and is not automatically tested.

.. _permissions:

Permissions
-----------

Permission Levels
^^^^^^^^^^^^^^^^^

There are four levels of permission a ``User`` can have on a resource. These
levels are in a strict hierarchy with a higher permission level including all of
the permissions below it. The levels are:

1) No permission (cannot view, edit, or delete a resource)
2) ``READ`` permission (can view and download resources)
3) ``WRITE`` permission (includes ``READ`` permission, can edit the properties of a resource)
4) ``ADMIN`` also known as ``own`` permission,  (includes ``READ`` and ``WRITE`` permission, can delete
   the resource and also control access on it)

A site administrator always has permission to take any action.

Permission Model
^^^^^^^^^^^^^^^^

Permissions are resolved at the level of a ``User``, i.e., for any ``User``, an
attempt to take a certain action will be allowed or disallowed based on the
permissions for that ``User``, as a function of the resource, the operation, the
permissions set on that resource for that ``User``, and the permissions set on
that resource by any ``Groups`` the ``User`` is a member of.

Permissions are always additive.  That is, given a ``User`` with a certain
permission on a resource, that permission can not be taken away from the
``User`` by addition of other permissions to the system, but only through
removing existing permissions to that ``User`` or removing that ``User`` from a
``Group``.  Once again, a site admin always has permission to take any action.

Collections
^^^^^^^^^^^

``Collections`` can be ``Public`` (meaning viewable even by anonymous users) or
``Private`` (meaning viewable only by those with ``READ`` access).
``Collections`` can have permissions set on them at the individual ``User``
level and ``Group`` level, meaning that a given ``User`` or ``Group`` can have
``READ``, ``WRITE``, or ``ADMIN`` permissions set on the ``Collection``.


Folders
^^^^^^^

``Folders`` can be ``Public`` (meaning viewable even by anonymous users) or
``Private`` (meaning viewable only by those with ``READ`` access).  ``Folders``
can have permissions set on them at the individual ``User`` level and ``Group``
level, meaning that a given ``User`` or ``Group`` can have ``READ``, ``WRITE``,
or ``ADMIN`` permissions set on the ``Folder``.  ``Folders`` inherit permissions
from their parent ``Folder``.

Items
^^^^^

``Items`` always inherit their permissions from their parent ``Folder``. Each
access-controlled resource (e.g., ``Folder``, ``Collection``) has a list of
permissions granted on it, and each item in that list is a mapping of either
``Users`` to permission level or ``Groups`` to permission level.  This is best
visualized by opening the "Access control" dialog on a ``Folder`` in the
hierarchy. The actual permission level that a ``User`` has on that resource is
defined as: the maximum permission level available based on the permissions
granted to any ``Groups`` that the ``User`` is member of, or permissions granted
to that ``User`` specifically.

Groups
^^^^^^

For access control, ``Groups`` can be given any level of access to a resource
that an individual ``User`` can, and this is managed at the level of the
resource in question.

For permissions on ``Groups`` themselves, ``Public`` Groups are viewable
(``READ`` permission) to anyone, even anonymous users.  ``Private`` ``Groups``
are not viewable or even listable to any ``Users`` except those that are members
of the ``Group``, or those that have been invited to the ``Group``.

``Groups`` have three levels of roles that ``Users`` can have within the
``Group``.  They can be ``Members``, ``Moderators`` (also indicates that they
are ``Members``), and ``Administrators`` (also indicates that they are
``Members``).

``Users`` that are not ``Members`` of a group can request to become ``Members``
of a ``Group`` if that ``Group`` is ``Public``.

``Members`` of a ``Group`` can see the membership list of the ``Group``,
including roles, and can see pending requests and invitations for the group.  If
a ``User`` has been invited to a ``Group``, they have ``Member`` access to the
``Group`` even before they have accepted the invitation.  A ``Member`` of a
``Group`` can leave the group, at which point they are no longer ``Members`` of
the ``Group``.

``Moderators`` of a ``Group`` have all of the abilities of ``Group``
``Members``.  ``Moderators`` can also invite ``Users`` to become ``Members``,
can accept or reject a request by a ``User`` to become a ``Member``, can remove
``Members`` or ``Moderators`` from the ``Group``, and can edit the ``Group``
which includes changing the name and description and changing the
``Public``/``Private`` status of the ``Group``.

``Administrators`` of a ``Group`` have all of the abilities of ``Group``
``Moderators``.  ``Administrators`` can also delete the ``Group``, promote a
``Member`` to ``Moderator`` or ``Administrator``, demote an ``Administrator`` or
``Moderator`` to ``Member``, and remove any ``Member``, ``Moderator``, or
``Administrator`` from the ``Group``.

The creator of a ``Group`` is an ``Administrator`` of a group.  Any logged in
``User`` can create a ``Group``.

User
^^^^

``Users`` have ``ADMIN`` access on themselves, and have ``READ`` access on other
``Users``.

.. _api_keys:

API keys
--------

Like many web services, Girder's API is designed for programmatic interaction.
API keys can facilitate these sorts of interactions -- they enable client applications
to interact with the server on behalf of your user without actually authenticating with
your password. They can also be granted restricted access to only a limited set of functionality
of the API.

Under the **My account** page, there is a tab called **API keys** where these keys can be
created and managed. You can have many API keys; in fact, it's recommended to use a
different key for each different client application that needs authenticated access
to the Girder server. By convention, the **Name** field of API keys can be used to
specify what application is making use of the key in a human-readable way, although
you may name your keys however you want.

Each API key can be used to gain authentication tokens just like when you log in
with a username and password. If you want to limit the maximum amount of time that
these tokens last, you can do so on a per-key basis, or leave the token duration
field empty to use the server default.

When creating and updating API keys, you can also select among two modes: you can
either grant full access to the API key, which gives unrestricted API access as
though you are logged in as your user, or you can choose limited functionality scopes
from a list of checkboxes to restrict the sorts of actions that the key will allow.

It is also possible to deactivate a key temporarily. If you deactivate an existing
key, it will immediately delete all active tokens created with that key, and also
stop that key from being able to create new tokens until you activate it once again.
Alternatively, you can delete the key altogether, which will make the key and any
tokens created with it never work again.


Using Girder CLI to Upload and Download data
============================================

See :ref:`python-client`
