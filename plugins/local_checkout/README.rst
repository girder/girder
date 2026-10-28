local-checkout
==============

A Girder plugin that lets users temporarily "check out" the contents of a
folder from an S3 assetstore to a filesystem assetstore.

Files on S3 assetstores are copied to a filesystem assetstore for a chosen
number of days; while checked out, Girder serves the local copy.  When a
checkout expires, or when the filesystem assetstore runs short of space, the
local copies are removed and the files once again refer to the S3 data they
came from.

See the Girder documentation for details.
