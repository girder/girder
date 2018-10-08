import json
import os
import pprint
import sys
import time

cmd = 'curl --silent 127.0.0.1:8080/api/v1/system/version'
maxWait = 60
startTime = time.time()
while time.time() - startTime < maxWait:
    try:
        output = json.loads(os.popen(cmd).read())
        if 'apiVersion' in output:
            break
    except Exception:
        pass
    time.sleep(1)
    sys.stderr.write('.')
    sys.stderr.flush()
else:
    sys.stderr.write('Girder failed to start\n')
    sys.exit(1)
sys.stderr.write('\n')
pprint.pprint(output)
