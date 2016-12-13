module.exports = {
  "extends": "semistandard",
  "rules": {
    "indent": [
      2,
      4,
      {
        "SwitchCase": 1
      }
    ],
    "space-before-function-paren": [
      2,
      {
        "anonymous": "always",
        "named": "never"
      }
    ],
    "one-var": 0,
    "no-multi-spaces": [
      2,
      {
        "exceptions": {
          "VariableDeclarator": true,
          "ImportDeclaration": true
        }
      }
    ],
    "backbone/collection-model": 2,
    "backbone/defaults-on-top": 0,
    "backbone/event-scope": 0,
    "backbone/events-on-top": [2, ["tagName", "className"]],
    "backbone/events-sort": 0,
    "backbone/initialize-on-top": [2, {
      View: ["tagName", "className", "events"],
      Model: ["defaults", "url", "urlRoot"],
      Collection: ["model", "url"]
    }],
    "backbone/model-defaults": 0,
    "backbone/no-changed-set": 0,
    "backbone/no-collection-models": 0,
    "backbone/no-constructor": 2,
    "backbone/no-el-assign": 0,
    "backbone/no-model-attributes": 2,
    "backbone/no-native-jquery": 0,
    "backbone/no-silent": 0,
    "backbone/no-view-collection-models": 2,
    "backbone/no-view-model-attributes": 0,
    "backbone/no-view-onoff-binding": 0,
    "backbone/no-view-qualified-jquery": 0,
    "backbone/render-return": 0,
    "underscore/collection-return": 2,
    "underscore/matches-shorthand": [
      2,
      "always"
    ],
    "underscore/no-unnecessary-bind": 2,
    "underscore/prefer-compact": 2,
    "underscore/prefer-constant": 2,
    "underscore/prefer-filter": 2,
    "underscore/prefer-findwhere": 2,
    "underscore/prefer-invoke": 2,
    "underscore/prefer-map": 2,
    "underscore/prefer-matches": 2,
    "underscore/prefer-noop": 0,
    "underscore/prefer-pluck": 2,
    "underscore/prefer-reject": 2,
    "underscore/prefer-times": 2,
    "underscore/prefer-underscore-method": 0,
    "underscore/prefer-underscore-typecheck": 2,
    "underscore/prefer-where": 2,
    "underscore/preferred-alias": 2,
    "underscore/prop-shorthand": [
      2,
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
    "_": true,
    "girder": true,
    "Backbone": true,
    "Remarkable": true,
    "JSONEditor": true,
    "sprintf": true
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
