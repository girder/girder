
//
// This script allows to conveniently expand relative path in JSON config file.
//

// Describe script parameters and parse arguments

var path = require('path');
var _ = require('underscore');

var scriptname = path.basename(process.argv[1]);

var argv = require('argv');

argv.info(
  'This script allows to expand relative path in a JSON config file.\n' +
  '\nUsage:\n' +
  '\n  ' + scriptname + ' [-v] [-b /path/to/base] -k key1 [-k key2 [...]] -i /path/to/input.js [-o /path/to/output.js]\n' +
  '\nArgument description:'
);

var args = argv.option([
    {
        name: 'verbose',
        short: 'v',
        type: 'boolean',
        description: 'Display additional information'
    },
    {
        name: 'base_dir',
        short: 'b',
        type: 'path',
        description: 'Base directory used when transforming selected paths. If not specified, directory of the config file is used.'
    },
    {
        name: 'relative_path_key',
        short: 'k',
        type: 'list,string',
        description: 'Config key(s) matching <relative_path_key> will be transformed to an absolute path using config file directory as a base',
        example: '-k excludeFiles'
    },
    {
        name: 'inputfile',
        short: 'i',
        type: 'path',
        description: 'Config file to expand'
    },
    {
        name: 'outputfile',
        short: 'o',
        type: 'path',
        description: 'Place the updated config file into <outputfile>'
    }
]).run();

if (Object.keys(args.options).length === 0 ||
   (Object.keys(args.options).length === 1 && 'verbose' in args.options)) {
    argv.help();
    process.exit(-1);
}

var verbose = args.options.verbose;
var base_dir = args.options.base_dir;
var inputfile = args.options.inputfile;
var outputfile = args.options.outputfile;
var relative_path_keys = args.options.relative_path_key;

if (!inputfile) {
    console.log('\nMissing \'--outputfile\' argument.');
    argv.help();
    process.exit(-1);
}

if (!relative_path_keys) {
    console.log('\nMissing \'--relative_path_key\' argument.');
    argv.help();
    process.exit(-1);
}

if (!base_dir) {
    base_dir = path.dirname(inputfile);
}

if (verbose) {
    console.log('Using base_dir ' + base_dir);
}

// Read config file

var fs = require('fs');
var json = require('comment-json');

if (verbose) {
    console.log('Reading ' + inputfile);
}
var config = json.parse(fs.readFileSync(inputfile, {encoding: 'utf8'}).toString());

// Expand relative paths

if (!_.isFunction(String.prototype.startsWith)) {
    String.prototype.startsWith = function (str) { // eslint-disable-line no-extend-native
        return this.slice(0, str.length) === str;
    };
}

var expand_relative_path = function (key, value) {
    if (relative_path_keys.indexOf(key) >= 0) {
        // XXX Nodejs (>= v0.11.2) has "path.isAbsolute"
        if (value.startsWith('.')) {
            return base_dir + '/' + value;
        }
    }
    return value;
};

var expand_relative_paths = function (arr1, current_key) {
    var idx = '';

    if (arr1 && Object.prototype.toString.call(arr1) === '[object Array]') {
        for (idx in arr1) {
            if (arr1.hasOwnProperty(idx)) {
                arr1[idx] = expand_relative_path(current_key, arr1[idx]);
            }
        }
    } else if (arr1 && (arr1 instanceof Object)) {
        for (idx in arr1) {
            if (arr1.hasOwnProperty(idx)) {
                if (idx in arr1) {
                    if (_.isObject(arr1[idx])) {
                        arr1[idx] = expand_relative_paths(arr1[idx], idx);
                    } else {
                        arr1[idx] = expand_relative_path(idx, arr1[idx]);
                    }
                }
            }
        }
    }

    return arr1;
};

var updated_config = expand_relative_paths(config);

// Save updated config

var output = json.stringify(updated_config, null, 4);

output += '\n';

if (outputfile) {
    if (verbose) {
        console.log('Outputing updated config file to ' + outputfile);
    }
    fs.writeFileSync(outputfile, output);
} else {
    if (verbose) {
        console.log('Outputing updated config to <stdout>:');
    }
    console.log(output);
}
