import collections
import os
import six
import subprocess

Tree = lambda: collections.defaultdict(Tree)

EXCLUDE_DIRS = ['test', 'tests', 'plugin_tests']

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
        # Skip imported symbols
        '--python-kinds=-i',
        filePath
    ]).decode('utf-8')

    for fileTag in fileTags.splitlines():
        symbolName, symbolFileName, symbolRegex, symbolExtensions = fileTag.split('\t', 3)
        symbolExtensions = symbolExtensions.split('\t')
        symbolAbbrviatedKind = symbolExtensions[0]
        if len(symbolExtensions) >= 2:
            # Symbol is scoped
            symbolScopeKind, symbolScope = symbolExtensions[1].split(':')
            if symbolScopeKind == 'class':
                pass
            elif symbolScopeKind == 'function':
                # Symbols defined inside functions are not visible
                continue
            else:
                raise Exception('Unknown symbol scope')
            symbolScope = symbolScope.split('.')
        else:
            symbolScope = []
        symbolScope.append(symbolName)

        addSymbol(symbolScope, symbolTree)


def addDirSymbols(dirPath, symbolTree):
    for subName in os.listdir(dirPath):
        subPath = os.path.join(dirPath, subName)
        if os.path.isdir(subPath) and subName not in EXCLUDE_DIRS:
            addDirSymbols(subPath, symbolTree[subName])
        elif os.path.isfile(subPath):
            subNameBase, subNameExt = os.path.splitext(subName)
            if subNameExt != '.py':
                continue
            if subName == '__init__.py':
                # '__init__.py' adds symbols to the module-level tree
                addFileSymbols(subPath, symbolTree)
            else:
                addFileSymbols(subPath, symbolTree[subNameBase])


def printTree(symbolTree, level=0):
    for symbol, subTree in sorted(six.viewitems(symbolTree)):
        if symbol.startswith('_') and symbol != '__init__.py':
            continue
        print(' '*(level * 4) + symbol)
        printTree(subTree, level+1)


def main():
    rootPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    baseTree = Tree()
    addDirSymbols(
        os.path.join(rootPath, 'girder'),
        baseTree['girder']
    )
    addDirSymbols(
        os.path.join(rootPath, 'plugins'),
        baseTree['plugins']
    )

    printTree(baseTree)


if __name__ == '__main__':
    main()
