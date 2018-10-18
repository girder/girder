#!/usr/bin/env bash

set +e
DIFF=$(diff scripts/publicNames.txt <(python scripts/publicNames.py))
if [ "$DIFF" != "" ]; then

diff scripts/publicNames.txt <(python scripts/publicNames.py)

cat << EOF

**********************************************************

Public symbols have been introduced (or removed) and those
changes have not been commited to the scripts/publicNames.txt
file. Please run the following command:

  python scripts/publicNames.py > scripts/publicNames.txt

from the root of your local repository and commit the
changes to scripts/publicNames.txt
**********************************************************

EOF
exit 1;
fi
