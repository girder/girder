module.exports = {
  "extends": "semistandard",
  "rules": {
    "indent": [
      "error",
      4,
      {
        "SwitchCase": 1
      }
    ],
    "space-before-function-paren": [
      "error",
      {
        "anonymous": "always",
        "named": "never"
      }
    ],
    "one-var": "off",
    "no-multi-spaces": [
      "error",
      {
        "exceptions": {
          "VariableDeclarator": true,
          "ImportDeclaration": true
        }
      }
    ],
    "backbone/collection-model": "error",
    "backbone/defaults-on-top": "off",
    "backbone/event-scope": "off",
    "backbone/events-on-top": ["error", ["tagName", "className"]],
    "backbone/events-sort": "off",
    "backbone/initialize-on-top": ["error", {
      View: ["tagName", "className", "events"],
      Model: ["defaults", "url", "urlRoot"],
      Collection: ["model", "url"]
    }],
    "backbone/model-defaults": "off",
    "backbone/no-changed-set": "off",
    "backbone/no-collection-models": "off",
    "backbone/no-constructor": "error",
    "backbone/no-el-assign": "off",
    "backbone/no-model-attributes": "error",
    "backbone/no-native-jquery": "off",
    "backbone/no-silent": "off",
    "backbone/no-view-collection-models": "error",
    "backbone/no-view-model-attributes": "off",
    "backbone/no-view-onoff-binding": "off",
    "backbone/no-view-qualified-jquery": "off",
    "backbone/render-return": "off",
    "underscore/collection-return": "error",
    "underscore/matches-shorthand": [
      "error",
      "always"
    ],
    "underscore/no-unnecessary-bind": "error",
    "underscore/prefer-compact": "error",
    "underscore/prefer-constant": "error",
    "underscore/prefer-filter": "error",
    "underscore/prefer-findwhere": "error",
    "underscore/prefer-invoke": "error",
    "underscore/prefer-map": "error",
    "underscore/prefer-matches": "error",
    "underscore/prefer-noop": "off",
    "underscore/prefer-pluck": "error",
    "underscore/prefer-reject": "error",
    "underscore/prefer-times": "error",
    "underscore/prefer-underscore-method": "off",
    "underscore/prefer-underscore-typecheck": "error",
    "underscore/prefer-where": "error",
    "underscore/preferred-alias": "error",
    "underscore/prop-shorthand": [
      "error",
      "always"
    ]
  },
  "env": {
    "browser": true,
    "jquery": true
  },
  "plugins": [
    "backbone",
    "underscore"
  ],
  "globals": {
  },
  "settings": {
    "backbone": {
      "Collection": [
        "girder.Collection"
      ],
      "Model": [
        "girder.Model"
      ],
      "View": [
        "girder.View",
        "girder.views.MetadatumEditWidget"
      ]
    }
  }
};
