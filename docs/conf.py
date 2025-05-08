import pkg_resources

from sphinx.domains.python import PythonDomain

# needs_sphinx = '1.6'

# Get package imports and version
# The 'girder' and "girder_client" packages must be installed at this point
_girder_package = pkg_resources.get_distribution('girder')
_girder_client_package = pkg_resources.get_distribution('girder_client')
_girder_version = _girder_package.version
_girder_imports = {
    _requirement.project_name.lower()
    for _package in [_girder_package, _girder_client_package]
    for _requirement in _package.requires(_package.extras)
}
# Add importable module names that are different from package names
_girder_imports |= {
    'botocore',
    'bson',
    'dateutil',
    'dogpile',
    'requests_toolbelt',
    'yaml'
}

# Set Sphinx variables
master_doc = 'index'

project = 'Girder'
copyright = '2014-2018, Kitware, Inc.'
release = _girder_version
version = '.'.join(release.split('.')[:2])

html_theme = 'sphinx_rtd_theme'
html_favicon = 'favicon.ico'

latex_documents = [
    ('index', 'Girder.tex', 'Girder Documentation', 'Kitware, Inc.', 'manual'),
]

# Setup Sphinx extensions (and associated variables)
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxcontrib.jquery',
]

autodoc_mock_imports = list(_girder_imports)

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}


# Override the resolution of some targets
class PatchedPythonDomain(PythonDomain):
    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # References to "list" may ambiguously resolve to several Girder methods named "list",
        # instead of just the built-in Python 'list' (due to the mechanism described at
        # http://www.sphinx-doc.org/en/stable/domains.html#role-py:obj ). This results in incorrect
        # xrefs and causes Sphinx to emit warnings. So, rather than require all references to
        # explicitly name ":py:obj:`list`", override this method to do the right thing.
        if target == 'list':
            # References to built-in symbols natively return None
            return None
        return super().resolve_xref(
            env, fromdocname, builder, typ, target, node, contnode)


def setup(sphinx):
    sphinx.add_domain(PatchedPythonDomain, override=True)
