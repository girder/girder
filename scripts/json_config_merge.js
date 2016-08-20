
//
// This script allows to conveniently merge multiple JSON config files.
//

// Describe script parameters and parse arguments

var path = require('path');
var _ = require('underscore');

var scriptname = path.basename(process.argv[1]);

var argv = require('argv');

argv.info(
  'This script allows to merge multiple JSON config files.\n' +
  '\nUsage:\n' +
  '\n  ' + scriptname + ' [-v] -o /path/to/output.js ' +
  ' -i /path/to/config1.js -i /path/to/config2.js [-i /path/to/config3.js [...]]\n' +
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
        name: 'outputfile',
        short: 'o',
        type: 'path',
        description: 'Place the merged config files into <outputfile>'
    },
    {
        name: 'inputfile',
        short: 'i',
        type: 'list,path',
        description: 'Config file to merge',
        example: '-i /path/to/config1.js -i /path/to/config2.js [-i /path/to/config3.js [...]]'
    }
]).run();

if (Object.keys(args.options).length === 0 ||
   (Object.keys(args.options).length === 1 && 'verbose' in args.options)) {
    argv.help();
    process.exit(-1);
}

var verbose = args.options.verbose;
var inputfiles = args.options.inputfile;
var outputfile = args.options.outputfile;

if (!outputfile) {
    console.log('\nMissing \'--outputfile\' argument.');
    argv.help();
    process.exit(-1);
}

if (inputfiles.length < 2) {
    console.log('\nAt least two config files should be specified.');
    argv.help();
    process.exit(-1);
}

// Read config files

var fs = require('fs');
var json = require('comment-json');

var configs = [];
inputfiles.forEach(function (val) {
    var configFile = val;

    if (verbose) {
        console.log('Reading ' + configFile);
    }
    configs.push(json.parse(fs.readFileSync(configFile, {encoding: 'utf8'}).toString()));
});

// Merge configs

function arrayMergeRecursive(arr1, arr2) {
    //  discuss at: http://phpjs.org/functions/array_merge_recursive/
    // original by: Subhasis Deb
    //    input by: Brett Zamir (http://brett-zamir.me)
    // bugfixed by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    //  depends on: array_merge
    //   example 1: arr1 = {'color': {'favourite': 'read'}, 0: 5}
    //   example 1: arr2 = {0: 10, 'color': {'favorite': 'green', 0: 'blue'}}
    //   example 1: array_merge_recursive(arr1, arr2)
    //   returns 1: {'color': {'favorite': {0: 'red', 1: 'green'}, 0: 'blue'}, 1: 5, 1: 10}

    var idx = '';

    if (arr1 && Object.prototype.toString.call(arr1) === '[object Array]' &&
        arr2 && Object.prototype.toString.call(arr2) === '[object Array]') {
        for (idx in arr2) {
            if (arr2.hasOwnProperty(idx)) {
                arr1.push(arr2[idx]);
            }
        }
    } else if ((arr1 && (arr1 instanceof Object)) && (arr2 && (arr2 instanceof Object))) {
        for (idx in arr2) {
            if (arr2.hasOwnProperty(idx)) {
                if (idx in arr1) {
                    if (_.isObject(arr1[idx]) && _.isObject(arr2)) {
                        arr1[idx] = arrayMergeRecursive(arr1[idx], arr2[idx]);
                    } else {
                        arr1[idx] = arr2[idx];
                    }
                } else {
                    arr1[idx] = arr2[idx];
                }
            }
        }
    }

    return arr1;
}

var mergedConfigs = configs[0];
configs.slice(1).forEach(function (config) {
    mergedConfigs = arrayMergeRecursive(mergedConfigs, config);
});

// Save merged configs

if (verbose) {
    console.log('Output file ' + outputfile);
}

var output = json.stringify(mergedConfigs, null, 4);

output += '\n';

fs.writeFileSync(outputfile, output);
