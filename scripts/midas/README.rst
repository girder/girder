Midas to Girder Migration
=========================

This folder contains scripts for migrating data from Midas to Girder.

It can migrate users, collections (communities in Midas), folders, items, item
metadata, and files (bitstreams in Midas).

It can optionally perform multiple operations in parallel to speed up the
migration (see ``N_JOBS``).

It records its progress to a local SQLite database. If the migration fails for
any reason, it can be restarted and the script will skip entities that have
already been migrated.

Since Midas users do not have a username, only an email address, the script will
generate a username based on the first and last name of the user. When
duplicates exist, or when the username is too short, numbers will be appended.

Users are assigned new passwords that are randomly generated. These are logged
to stdout. The random password generation is seeded with the username so that
multiple runs of the script will generate the same password for a given user.

Large migrations are difficult and take a while. Failures are to be expected.

Migrating
---------

First, edit migrate.py to set the configuration parameters at the top,
including the API endpoints and API keys.

Then, run the migration script::

    python migrate.py

The progress will be logged to stdout. You might want to redirect it to a file
so you have a record of it.

Verifying
---------

``walk_midas.py`` and ``walk_girder.py`` are provided to help verify that the
migration was successful. These print out breadcrumbs of all items. This output
can be saved to files and then diffed to see the differences.
