## Merge Base

We're in the middle of the Girder 3 merge window. This means that all new pull
requests need to be opened against the *master* branch since that's where Girder
3 is actively being developed. Note, this does not apply to fixes of bugs that only 
occur in Girder 2.

If this is a feature that needs to be included in Girder 2, an additional pull
request needs to be opened against the *2.x-maintenance* branch. It is recommended to
get your PR approved and merged into master first, then open a backport PR if needed,
so that any changes that need to be made during review don't have to be duplicated.
