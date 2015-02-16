import glob
import sys
import tarfile


package = glob.glob('girder-[0-9].*.tar.gz')
if not len(package):
    print('Could not find package archive')
    sys.exit(1)
if len(package) > 1:
    print('Error: multiple package versions found')
    sys.exit(1)

basename = package[0][:-7]  # remove '.tar.gz'

with tarfile.open(package[0], 'r:gz') as tar:
    headerMako = tar.getmember(basename + '/girder/mail_templates/_header.mako')
    if headerMako.size <= 0:
        print('Mail templates were not packaged properly')
        sys.exit(1)
