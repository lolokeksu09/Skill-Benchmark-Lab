import os,sys
receipt=os.environ.get('WFS_RESTORE_PROVIDER_RECEIPT')
if not receipt:
    print('Provider check unavailable: owner-issued WFS_RESTORE_PROVIDER_RECEIPT is missing',file=sys.stderr);sys.exit(2)
print('A configured receipt needs real provider validation; this offline fixture cannot perform it',file=sys.stderr)
sys.exit(2)
