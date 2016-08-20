
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
var baseDir = args.options.base_dir;
var inputfile = args.options.inputfile;
var outputfile = args.options.outputfile;
var relativePathKeys = args.options.relative_path_key;

if (!inputfile) {
    console.log('\nMissing \'--outputfile\' argument.');
    argv.help();
    process.exit(-1);
}

if (!relativePathKeys) {
    console.log('\nMissing \'--relative_path_key\' argument.');
    argv.help();
    process.exit(-1);
}

if (!baseDir) {
    baseDir = path.dirname(inputfile);
}

if (verbose) {
    console.log('Using base_dir ' + baseDir);
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

var expandRelativePath = function (key, value) {
    if (relativePathKeys.indexOf(key) >= 0) {
        // XXX Nodejs (>= v0.11.2) has "path.isAbsolute"
        if (value.startsWith('.')) {
            return baseDir + '/' + value;
        }
    }
    return value;
};

var expandRelativePaths = function (arr1, currentKey) {
    var idx = '';

    if (arr1 && Object.prototype.toString.call(arr1) === '[object Array]') {
        for (idx in arr1) {
            if (arr1.hasOwnProperty(idx)) {
                arr1[idx] = expandRelativePath(currentKey, arr1[idx]);
            }
        }
    } else if (arr1 && (arr1 instanceof Object)) {
        for (idx in arr1) {
            if (arr1.hasOwnProperty(idx)) {
                if (idx in arr1) {
                    if (_.isObject(arr1[idx])) {
                        arr1[idx] = expandRelativePaths(arr1[idx], idx);
                    } else {
                        arr1[idx] = expandRelativePath(idx, arr1[idx]);
                    }
                }
            }
        }
    }

    return arr1;
};

var updatedConfig = expandRelativePaths(config);

// Save updated config

var output = json.stringify(updatedConfig, null, 4);

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
