import json, os, urllib.request, time
from pathlib import Path
API='https://api.buffer.com'

def gql(key,q):
    req=urllib.request.Request(API,data=json.dumps({'query':q}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST')
    with urllib.request.urlopen(req,timeout=30) as r: p=json.loads(r.read().decode())
    if p.get('errors'): raise RuntimeError(json.dumps(p['errors'],ensure_ascii=False))
    return p['data']

def main():
    key=os.environ['BUFFER_API_KEY']
    path=Path('status/published-reel-01.json')
    st=json.loads(path.read_text())
    pid=st['buffer_result']['post']['id']
    post=None
    for _ in range(12):
        q=f'''query {{ post(input: {{ id: "{pid}" }}) {{ id text status sentAt externalLink sharedNow shareMode error {{ message }} }} }}'''
        post=gql(key,q)['post']
        if post.get('status') in ('sent','error'):
            break
        time.sleep(5)
    st['buffer_result']['post']=post
    st['verified_after_publish']=True
    path.write_text(json.dumps(st,ensure_ascii=False,indent=2))
    print(json.dumps(post,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
