import os,sys,urllib.request
url=os.environ.get("WFS_VALIDATION_SERVICE_ORIGIN")
if not url:
    print("Integration unavailable: WFS_VALIDATION_SERVICE_ORIGIN is not configured",file=sys.stderr)
    sys.exit(2)
with urllib.request.urlopen(url+"/health",timeout=3) as response:
    assert response.status==200
