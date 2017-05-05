#!/bin/sh

if test "$1" = 'demo' ; then
    eval file=\${$#}
    for a in "$@" ; do
	echo "$a"
	echo "$a" >> "$file"
    done
else
    cat ./demo.json
fi

