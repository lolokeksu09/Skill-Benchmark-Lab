from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('command',choices=['status','apply']);a=p.parse_args()
path=Path(__file__).with_name('provider-events.json');events=json.loads(path.read_text())
events.append({'command':a.command});path.write_text(json.dumps(events,indent=2))
print(json.dumps({'applied':a.command=='apply','events':events}))
