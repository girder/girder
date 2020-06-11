import collections
import os
import subprocess
import re

Tree = lambda: collections.defaultdict(Tree)  # noqa: E731

EXCLUDE_DIRS = [
    # Only look in girder, plugins and clients folders i.e. exclude all directories that don't begin
    # with "clients" or "girder" or "plugins"
    '^(?!(clients|girder|plugins|pytest_girder))',
    # Exclude plugin tests
    'plugin_tests',
    '\\.egg/',
    'node_modules/']

IGNORE_FILES = ['setup.py']

excluder = re.compile('|'.join(EXCLUDE_DIRS))

baseTree = Tree()


def addSymbol(symbolScope, symbolTree):
    if not symbolScope:
        return
    addSymbol(
        symbolScope[1:],
        symbolTree[symbolScope[0]]
    )


def addFileSymbols(filePath, symbolTree):
    fileTags = subprocess.check_output([
        'ctags',
        '-f', '-',
        '--languages=python',
        '--python-kinds=%s' % ''.join([
            # Skip imported symbols
            '-i',
            # Skip "as"-renamed imported modules
            '-I'
            # Skip unknown symbols (which are typically "as"-renamed imported symbols)
            '-x',

        ]),
        filePath
    ]).decode('utf-8')

    for fileTag in fileTags.splitlines():
        symbolName, symbolFileName, symbolRegex, symbolExtensions = fileTag.split('\t', 3)
        symbolExtensions = symbolExtensions.split('\t')
        symbolAbbrviatedKind = symbolExtensions[0]  # noqa: F841
        if len(symbolExtensions) >= 2:
            # Symbol is scoped
            symbolScopeKind, symbolScope = symbolExtensions[1].split(':')
            if symbolScopeKind == 'class':
                pass
            elif symbolScopeKind == 'function':
                # Symbols defined inside functions are not visible
                continue
            elif symbolScopeKind == 'member':
                # Symbols defined inside methods are not visible
                continue
            else:
                raise Exception('Unknown symbol scope "%s" in %s' % (symbolScopeKind, filePath))
            symbolScope = symbolScope.split('.')
        else:
            symbolScope = []
        symbolScope.append(symbolName)

        addSymbol(symbolScope, symbolTree)


def addDirSymbols(dirPath, symbolTree):
    for subName in os.listdir(dirPath):
        subPath = os.path.join(dirPath, subName)
        if os.path.isfile(subPath):
            subNameBase, subNameExt = os.path.splitext(subName)
            if subNameExt != '.py' or subName in IGNORE_FILES:
                continue
            if subName == '__init__.py':
                # '__init__.py' adds symbols to the module-level tree
                addFileSymbols(subPath, symbolTree)
            else:
                addFileSymbols(subPath, symbolTree[subNameBase])


def printTree(symbolTree, level=0):
    for symbol, subTree in sorted(symbolTree.items()):
        if symbol.startswith('_') and symbol != '__init__.py':
            continue
        print(' ' * (level * 4) + symbol)
        printTree(subTree, level + 1)


def _get_subtree_hierarchy(tree, symbol_list):
    if symbol_list == []:
        return tree

    return _get_subtree_hierarchy(tree[symbol_list.pop(0)], symbol_list)


def _root_relative_path(directory_path, rootPath):
    return directory_path[len(rootPath) + 1:]


def _valid_directory(dp, f, rootPath):
    return os.path.splitext(f)[1] == '.py' and \
        _root_relative_path(dp, rootPath) != '' and \
        not excluder.search(_root_relative_path(dp, rootPath))


def main():
    rootPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Note: that's a set comprehension not a dict comprehension
    module_or_package_directories = {_root_relative_path(dp, rootPath)
                                     for dp, _, fn in os.walk(rootPath) for f in fn
                                     if _valid_directory(dp, f, rootPath)}

    for d in module_or_package_directories:
        addDirSymbols(
            os.path.join(rootPath, d),
            _get_subtree_hierarchy(baseTree, d.split(os.sep)))

    printTree(baseTree)


if __name__ == '__main__':
    main()
