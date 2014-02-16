# Open Questions for this document

* Are privileges always additive?
* Can Items take privileges from Groups and Folders, some combination?
* Can Items be contained in non-leaf folders?
* Can Items be duplicated/shared accross different folders?  What are the analogous operations in Girder to the share/link/clone/duplicate stuff in Midas?

# Areas to address in this document

* Group admin/management



# Girder

Girder is a Data Management Toolkit.  It is a complete back-end (server side) technology that can be used with other applications via its RESTful API, or it can be used via its own front-end (client side web pages and JavaScript).

Our aims for Girder is for it to be robust, performant, extensible, and grokable. 

Girder is built in Python.  For installation and deployment, see the [README](../README.md).

Girder is open source, distributed with the [Apache 2.0 license](../LICENSE).

## Document Conventions

This document is written for end-users of Girder, rather than developers.  Since it was written by developers, sometimes we fail at making this distinction, please remind (and forgive) us.

Girder specific entities will be `formatted like this`.

## Concepts

### Users

This is a common software concept, nice that we didn't change its established meaning!  Each user of Girder should have a `User` created within Girder.  Their Girder `User` will determine their privileges and can store and share their data.

### Groups

A Girder `Group` is a collection of Girder `Users`, with a common set of privileges and access to data.

### Items

A Girder `Item` is an atomic file (cannot be separated into smaller parts within Girder).  This could be a collection of files (or tar, zip, etc), but from Girder's persective it is considered an atomic file.  `Items` in Girder do not have privileges set on them, they inherit privileges by virtue of living in a `Folder` or TODO WHATSADEAL? some `Group` interaction. OPEN QUESTIONS.

### Folders

A Girder `Folder` is the common software concept of a folder, namely a hierarchically nested organizational structure.  Girder `Folders` can contain other `Folders` and also `Items`. OPEN QUESTION. `Folders` in Girder have privileges set on them, and the `Items` within them inherit privileges from their containing `Folders`.

