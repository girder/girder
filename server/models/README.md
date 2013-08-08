# Models

Models are classes that proxy data from the persistence layer. Validation of update or
create operations on objects should be performed in the model layer.

## Methods

#### load

    load(self, id, objectId=True)

*TODO*

#### save

    save(self, document)

*TODO*

#### find

    find(self, query={}, offset=0, limit=50, sort=None, fields=None)

*TODO*

#### remove

    remove(self, document)

*TODO*

## AccessControlledModel

The **AccessControlledModel** is a special subclass of **Model** that manages permissions and
access control on its documents. Any type of document that might have some form of access
control policies should inherit from this to take advantage of the convenient methods it
provides.

#### load

    load(self, id, level=AccessType.ADMIN, user=None, objectId=True, force=False)

*TODO*

#### requireAccess

    requireAccess(self, doc, user=None, level=AccessType.READ)

*TODO*

#### hasAccess

    hasAccess(self, doc, user=None, level=AccessType.READ)

*TODO*

#### setUserAccess

    setUserAccess(self, doc, user, level, save=True)

*TODO*

#### setGroupAccess

    setGroupAccess(self, doc, group, level, save=True)

*TODO*

#### setPublic

    setPublic(self, doc, public, save=True)

*TODO*

## Writing your own model

*TODO*
