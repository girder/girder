# /// script
# requires-python = ">=3.9"
# ///

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path


def get_git_tracked_python_files(repo_root):
    result = subprocess.run(
        ['git', 'ls-files', '*.py'],
        capture_output=True, text=True, cwd=repo_root
    )
    if result.returncode != 0:
        return []
    return [repo_root / f for f in result.stdout.strip().split('\n') if f]


def collect_attribute_parts(node):
    if isinstance(node, ast.Attribute):
        parent = collect_attribute_parts(node.value)
        if parent is None:
            return None
        return parent + [node.attr]
    if isinstance(node, ast.Name):
        return [node.id]
    return None


def resolve_constant(node, constants):  # noqa
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Attribute):
        parts = collect_attribute_parts(node)
        if parts:
            for i in range(len(parts), 0, -1):
                dotted = '.'.join(parts[:i])
                remainder = parts[i:]
                if dotted in constants:
                    val = constants[dotted]
                    if isinstance(val, str) and not remainder:
                        return val
                    if isinstance(val, dict) and remainder:
                        for r in remainder:
                            if isinstance(val, dict) and r in val:
                                val = val[r]
                            else:
                                val = None
                                break
                        if isinstance(val, str):
                            return val
    if isinstance(node, ast.JoinedStr):
        pieces = []
        for v in node.values:
            r = resolve_constant(v, constants)
            if r is None:
                return None
            pieces.append(str(r))
        return ''.join(pieces)
    if isinstance(node, ast.FormattedValue):
        return resolve_constant(node.value, constants)
    return None


def collect_class_constants_flat(tree, prefix=''):
    results = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_prefix = f'{prefix}{node.name}'
            class_dict = {}
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                        results[f'{class_prefix}.{target.id}'] = item.value.value
                        class_dict[target.id] = item.value.value
            results[class_prefix] = class_dict
    return results


def collect_module_constants(tree):
    constants = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                constants[target.id] = node.value.value
    constants.update(collect_class_constants_flat(tree))
    return constants


def find_module_file(filepath, module_name, level):
    base = filepath.parent
    for _ in range(level - 1):
        base = base.parent
    if module_name:
        parts = module_name.split('.')
        candidate = base
        for part in parts:
            candidate = candidate / part
        if candidate.is_dir():
            init = candidate / '__init__.py'
            if init.exists():
                return init
        py = candidate.with_suffix('.py')
        if py.exists():
            return py
    else:
        init = base / '__init__.py'
        if init.exists():
            return init
    return None


def parse_file_cached(path, cache):
    path = path.resolve()
    if path not in cache:
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
            tree = ast.parse(source, filename=str(path))
            cache[path] = (tree, collect_module_constants(tree))
        except (SyntaxError, ValueError):
            cache[path] = (None, {})
    return cache[path]


def collect_imported_constants(filepath, tree, parse_cache):  # noqa
    constants = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        level = node.level or 0
        if level == 0:
            continue
        module_name = node.module or ''

        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name

            if module_name:
                full_module = module_name + '.' + name
                target_file = find_module_file(filepath, full_module, level)
                if target_file:
                    _, imported_constants = parse_file_cached(target_file, parse_cache)
                    module_dict = {}
                    for key, val in imported_constants.items():
                        constants[f'{asname}.{key}'] = val
                        if isinstance(val, dict):
                            module_dict[key] = val
                        elif '.' not in key:
                            module_dict[key] = val
                    if module_dict:
                        constants[asname] = module_dict
                    continue

                target_file = find_module_file(filepath, module_name, level)
                if target_file:
                    _, imported_constants = parse_file_cached(target_file, parse_cache)
                    for key, val in imported_constants.items():
                        if key == name or key.startswith(name + '.'):
                            suffix = key[len(name):]
                            constants[asname + suffix] = val
                    continue
            else:
                target_file = find_module_file(filepath, name, level)
                if target_file:
                    _, imported_constants = parse_file_cached(target_file, parse_cache)
                    module_dict = {}
                    for key, val in imported_constants.items():
                        constants[f'{asname}.{key}'] = val
                        if isinstance(val, dict):
                            module_dict[key] = val
                        elif '.' not in key:
                            module_dict[key] = val
                    if module_dict:
                        constants[asname] = module_dict
                    continue

                base = filepath.parent
                for _ in range(level - 1):
                    base = base.parent
                init = base / '__init__.py'
                if init.exists():
                    _, pkg_constants = parse_file_cached(init, parse_cache)
                    for key, val in pkg_constants.items():
                        if key == name or key.startswith(name + '.'):
                            suffix = key[len(name):]
                            constants[asname + suffix] = val
    return constants


def build_constants(filepath, tree, parse_cache):
    constants = collect_module_constants(tree)
    constants.update(collect_imported_constants(filepath, tree, parse_cache))
    return constants


def find_validator_keys(tree, constants):
    keys = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func_node = dec.func
            is_validator = False
            if isinstance(func_node, ast.Attribute) and func_node.attr == 'validator':
                is_validator = True
            if isinstance(func_node, ast.Name) and func_node.id == 'validator':
                is_validator = True
            if not is_validator:
                continue
            for arg in dec.args:
                if isinstance(arg, (ast.Set, ast.List, ast.Tuple)):
                    for elt in arg.elts:
                        val = resolve_constant(elt, constants)
                        if val and isinstance(val, str):
                            keys.append(val)
                else:
                    val = resolve_constant(arg, constants)
                    if val and isinstance(val, str):
                        keys.append(val)
    return keys


def find_os_environ_refs(tree, constants):  # noqa
    refs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute) and func.attr == 'getenv'
                    and isinstance(func.value, ast.Name) and func.value.id == 'os'):
                if node.args:
                    val = resolve_constant(node.args[0], constants)
                    if val and isinstance(val, str):
                        refs.append(val)
            if (isinstance(func, ast.Attribute) and func.attr == 'get'
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == 'environ'
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == 'os'):
                if node.args:
                    val = resolve_constant(node.args[0], constants)
                    if val and isinstance(val, str):
                        refs.append(val)
        if isinstance(node, ast.Subscript):
            if (isinstance(node.value, ast.Attribute)
                    and node.value.attr == 'environ'
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == 'os'):
                val = resolve_constant(node.slice, constants)
                if val and isinstance(val, str):
                    refs.append(val)
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, ast.In):
                    if (isinstance(comparator, ast.Attribute)
                            and comparator.attr == 'environ'
                            and isinstance(comparator.value, ast.Name)
                            and comparator.value.id == 'os'):
                        val = resolve_constant(node.left, constants)
                        if val and isinstance(val, str):
                            refs.append(val)
    return refs


def find_config_dict_env_vars(tree, module_constants):  # noqa
    refs = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name):
            continue
        varname = node.targets[0].id
        if not isinstance(node.value, ast.Dict):
            continue
        if 'Config' not in varname:
            continue
        env_pattern = None
        for fnode in ast.walk(tree):
            if not isinstance(fnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(fnode):
                if not isinstance(child, ast.JoinedStr):
                    continue
                parts = []
                for v in child.values:
                    if isinstance(v, ast.Constant):
                        parts.append(v.value)
                    elif isinstance(v, ast.FormattedValue):
                        parts.append('{key}')
                    else:
                        parts = None
                        break
                if parts and any(p == '{key}' for p in parts):
                    joined = ''.join(parts)
                    if varname in ast.dump(fnode):
                        env_pattern = joined
                        break
            if env_pattern:
                break
        if env_pattern:
            for key_node in node.value.keys:
                key_val = resolve_constant(key_node, module_constants)
                if key_val and isinstance(key_val, str):
                    env_var = env_pattern.replace('{key}', key_val.replace('.', '_').upper())
                    refs.append(env_var)
    return refs


def classify_path(filepath, repo_root, repo_label):
    rel = filepath.relative_to(repo_root)
    parts = rel.parts
    if 'plugins' in parts:
        idx = parts.index('plugins')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if repo_label == 'girder':
        return 'core'
    return repo_label


def setting_key_to_env(key):
    return f"GIRDER_SETTING_{key.replace('.', '_').upper()}"


def process_repo(repo_root, repo_label, exclude_pattern):
    py_files = get_git_tracked_python_files(repo_root)
    setting_entries = []
    environ_entries = []
    parse_cache = {}
    for filepath in py_files:
        rel = str(filepath.relative_to(repo_root))
        if exclude_pattern and exclude_pattern.search(rel):
            continue
        try:
            source = filepath.read_text(encoding='utf-8', errors='replace')
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, ValueError):
            continue
        constants = build_constants(filepath, tree, parse_cache)
        component = classify_path(filepath, repo_root, repo_label)
        for key in find_validator_keys(tree, constants):
            env_var = setting_key_to_env(key)
            setting_entries.append((env_var, key, component, repo_label, rel))
        for env_var in find_os_environ_refs(tree, constants):
            environ_entries.append((env_var, component, repo_label, rel))
        for env_var in find_config_dict_env_vars(tree, constants):
            environ_entries.append((env_var, component, repo_label, rel))
    return setting_entries, environ_entries


def main():
    parser = argparse.ArgumentParser(
        description='Find Girder environment variables from one or more git repos'
    )
    parser.add_argument(
        'repos', nargs='+', metavar='[LABEL=]PATH',
        help="One or more repo paths, optionally prefixed with a label and '='. "
             'Example: girder=/path/to/girder large_image=/path/to/large_image'
    )
    parser.add_argument(
        '--exclude', '-e', default=r'(^|/)(tests?|examples|\.circleci)/',
        help='Regex pattern for relative file paths to exclude (default: %(default)s)'
    )
    parser.add_argument(
        '--ex-name', '-x', default=r'^(CIRCLE_BRANCH|TOX_ENV_)',
        help='Regex pattern of variables to exclude (default: %(default)s)'
    )
    args = parser.parse_args()

    exclude_pattern = re.compile(args.exclude) if args.exclude else None
    exclude_name_pattern = re.compile(args.ex_name) if args.ex_name else None

    all_settings = []
    all_environ = []

    for spec in args.repos:
        if '=' in spec:
            label, path_str = spec.split('=', 1)
        else:
            path_str = spec
            label = Path(path_str).resolve().name
        repo_root = Path(path_str).resolve()
        if not (repo_root / '.git').exists():
            print(f'Warning: {repo_root} does not appear to be a git repository, skipping',
                  file=sys.stderr)
            continue
        settings, environs = process_repo(repo_root, label, exclude_pattern)
        all_settings.extend(settings)
        all_environ.extend(environs)

    seen_settings = {}
    for env_var, key, component, repo_label, path in all_settings:
        if env_var not in seen_settings:
            seen_settings[env_var] = (key, component, repo_label, path)

    seen_environ = {}
    for env_var, component, repo_label, path in all_environ:
        if env_var not in seen_environ:
            seen_environ[env_var] = (component, repo_label, path)

    print('# Girder Environment Variables\n')
    print('## Database-Stored Settings via Environment Variables\n')
    print('| Environment Variable | Setting Key | Component | Repo | Source File |')
    print('|---|---|---|---|---|')
    for env_var in sorted(seen_settings.keys()):
        key, component, repo_label, path = seen_settings[env_var]
        print(f'| `{env_var}` | `{key}` | {component} | {repo_label} | `{path}` |')

    print('\n## Direct Environment Variables\n')
    print('| Environment Variable | Component | Repo | Source File |')
    print('|---|---|---|---|')
    for env_var in sorted(seen_environ.keys()):
        component, repo_label, path = seen_environ[env_var]
        if exclude_name_pattern and exclude_name_pattern.search(env_var):
            continue
        print(f'| `{env_var}` | {component} | {repo_label} | `{path}` |')


if __name__ == '__main__':
    main()
