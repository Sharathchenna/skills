import json,sys
raw=open(sys.argv[1]).read(); d=json.loads(raw[raw.find('{'):])
print('ok', d.get('ok'))
def items(o):
    if isinstance(o,dict):
        if ('rule' in o or 'code' in o) and ('message' in o or 'severity' in o): yield o; return
        for v in o.values(): yield from items(v)
    elif isinstance(o,list):
        for v in o: yield from items(v)
for f in items(d):
    if f.get('severity')=='info': continue
    print(f.get('severity'),f.get('rule') or f.get('code'),'|',str(f.get('message'))[:200],'|',f.get('selector',''),'| t=',f.get('time',''))
