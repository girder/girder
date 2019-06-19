module.exports = {
    'extends': 'semistandard',
    'rules': {
        'arrow-parens': 'error',
        'eqeqeq': ['error',
            'always', { 'null': 'always' }
        ],
        'for-direction': 'error',
        'getter-return': 'error',
        'indent': ['error', 4, {
            'SwitchCase': 1
        }],
        'multiline-ternary': [
            'error',
            'always-multiline'
        ],
        'no-alert': 'error',
        'no-multi-spaces': ['error', {
            'exceptions': {
                'VariableDeclarator': true,
                'ImportDeclaration': true
            }
        }],
        'no-throw-literal': 'off', // This would be desirable, but interferes with use in Promise.then
        'one-var': 'off',
        'quotes': ['error', 'single', {
            'avoidEscape': true,
            'allowTemplateLiterals': true
        }],
        'space-before-function-paren': ['error', {
            'anonymous': 'always',
            'named': 'never'
        }],
        'switch-colon-spacing': 'error',
        'backbone/collection-model': 'error',
        'backbone/defaults-on-top': ['error', ['resourceName', 'url', 'urlRoot']],
        'backbone/event-scope': 'off',
        'backbone/events-on-top': ['error', ['tagName', 'className']],
        'backbone/events-sort': 'off',
        'backbone/initialize-on-top': ['error', {
            'View': ['tagName', 'className', 'events'],
            'Model': ['resourceName', 'url', 'urlRoot', 'defaults'],
            'Collection': ['model', 'resourceName', 'url']
        }],
        'backbone/model-defaults': 'off',
        'backbone/no-changed-set': 'error',
        'backbone/no-collection-models': 'error',
        'backbone/no-constructor': 'error',
        'backbone/no-el-assign': 'error',
        'backbone/no-model-attributes': 'error',
        'backbone/no-native-jquery': 'off',
        'backbone/no-silent': 'error',
        'backbone/no-view-collection-models': 'error',
        'backbone/no-view-model-attributes': 'error',
        'backbone/no-view-onoff-binding': 'off',
        'backbone/no-view-qualified-jquery': 'error',
        'backbone/render-return': 'error',
        'import/exports-last': 'error',
        'import/named': 'error',
        'import/order': ['error', {
            'groups': ['builtin', 'external', ['parent', 'sibling', 'index']],
            'newlines-between': 'always-and-inside-groups'
        }],
        'promise/always-return': 'error',
        'promise/no-native': 'error',
        'promise/no-nesting': 'error',
        'promise/no-return-in-finally': 'error',
        'promise/no-return-wrap': 'error',
        'underscore/collection-return': 'error',
        'underscore/identity-shorthand': ['error', 'always'],
        'underscore/jquery-each': ['error', 'never'],
        'underscore/jquery-proxy': ['error', 'never'],
        'underscore/matches-shorthand': ['error', 'always'],
        'underscore/no-return-value-from-each-iteratee': 'error',
        'underscore/no-unnecessary-bind': 'error',
        'underscore/prefer-compact': 'error',
        'underscore/prefer-constant': 'error',
        'underscore/prefer-filter': 'error',
        'underscore/prefer-findwhere': 'error',
        'underscore/prefer-invoke': 'error',
        'underscore/prefer-map': 'error',
        'underscore/prefer-matches': 'error',
        'underscore/prefer-noop': 'off',
        'underscore/prefer-pluck': 'error',
        'underscore/prefer-reject': 'error',
        'underscore/prefer-times': 'error',
        'underscore/prefer-underscore-method': 'off',
        'underscore/prefer-underscore-typecheck': 'error',
        'underscore/prefer-where': 'error',
        'underscore/preferred-alias': 'error',
        'underscore/prop-shorthand': ['error', 'always']
    },
    'env': {
        'browser': true
    },
    'plugins': [
        'backbone',
        'underscore'
    ],
    'settings': {
        'backbone': {
            'Collection': [
                'Collection'
            ],
            'Model': [
                'Model',
                'AccessControlledModel'
            ],
            'View': [
                'View',
                'MetadatumEditWidget'
            ]
        }
    }
};
