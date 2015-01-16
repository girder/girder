# This is used in our travis environment as a hack to kill the build early
# if we detect a bad condition on their VMs that we know will break the tests.
# Namely, when the cache value from vmstat is very low.
import subprocess
import sys

if __name__ == '__main__':
    out = subprocess.check_output('vmstat')
    line = [l for l in out.split('\n') if l][-1]
    cache = int(line.split()[5])

    if cache < 100:
        print '!!! ABORTING, LOW CACHE DETECTED: %d !!!' % cache
        sys.exit(1)
