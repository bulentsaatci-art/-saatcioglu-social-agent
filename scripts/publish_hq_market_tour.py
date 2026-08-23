import base64, json, os, subprocess, time, urllib.request
from pathlib import Path
from PIL import Image

REPO='bulentsaatci-art/-saatcioglu-social-agent'
PART_DIR=Path('payload/hq-market-tour-20260823')
MEDIA=Path('public/posts/market-tour-hq-20260823.jpg')
STATUS=Path('status/published-hq-market-tour.json')
RAW=f'https://raw.githubusercontent.com/{REPO}/main/{MEDIA.as_posix()}'
API='https://api.buffer.com'
TARGET='saatcioglusupermarket'
CAPTION='''Mordoğan’da bugün kısa bir market turu 👀\n\nSüt & peynir, atıştırmalıklar, temizlik ve ev ihtiyaçları…\n\nBir sonraki turda hangi reyonu görmek istersiniz? Yorumlara yazın 👇\n\n#Mordoğan #Karaburun #SaatçıoğluSupermarket'''

def gql(key,q):
    req=urllib.request.Request(API,data=json.dumps({'query':q}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r: p=json.loads(r.read().decode())
    if p.get('errors'): raise RuntimeError(json.dumps(p['errors'],ensure_ascii=False))
    return p['data']

def qs(v): return json.dumps(v,ensure_ascii=False)

def channel(key):
    orgs=gql(key,'query { account { organizations { id } } }')['account']['organizations']
    for org in orgs:
        chs=gql(key,f'''query {{ channels(input: {{ organizationId: {qs(org['id'])} }}) {{ id name displayName service isQueuePaused }} }}''')['channels']
        for ch in chs:
            names={str(ch.get('name','')).lower().replace('@',''),str(ch.get('displayName','')).lower().replace('@','')}
            if TARGET in names and ch.get('service')=='instagram':
                if ch.get('isQueuePaused'): raise RuntimeError('Instagram queue paused')
                return ch
    raise RuntimeError('Instagram channel not found')

def wait_public():
    for _ in range(30):
        try:
            req=urllib.request.Request(RAW,method='HEAD',headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=15) as r:
                if r.status==200 and int(r.headers.get('Content-Length') or 0)>300000: return
        except Exception: pass
        time.sleep(3)
    raise RuntimeError('HQ media is not publicly reachable at expected size')

def main():
    key=os.environ['BUFFER_API_KEY']
    parts=sorted(PART_DIR.glob('part*.b64'))
    if not parts: raise RuntimeError('HQ payload parts missing')
    encoded=''.join(p.read_text().strip() for p in parts)
    MEDIA.parent.mkdir(parents=True,exist_ok=True)
    MEDIA.write_bytes(base64.b64decode(encoded))
    with Image.open(MEDIA) as im:
        if im.size!=(1080,1350): raise RuntimeError(f'Quality gate failed dimensions={im.size}')
    if MEDIA.stat().st_size<300000: raise RuntimeError(f'Quality gate failed bytes={MEDIA.stat().st_size}')

    subprocess.run(['git','config','user.name','Saatcioglu Social Agent'],check=True)
    subprocess.run(['git','config','user.email','actions@users.noreply.github.com'],check=True)
    subprocess.run(['git','add',str(MEDIA)],check=True)
    subprocess.run(['git','commit','-m','Add HQ market tour post'],check=True)
    subprocess.run(['git','push'],check=True)
    wait_public()

    ch=channel(key)
    q=f'''mutation {{ createPost(input: {{ text: {qs(CAPTION)} channelId: {qs(ch['id'])} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ image: {{ url: {qs(RAW)} }} }}] metadata: {{ instagram: {{ type: post shouldShareToFeed: true }} }} }}) {{ ... on PostActionSuccess {{ post {{ id status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    result=gql(key,q)['createPost']
    if isinstance(result,dict) and result.get('message'): raise RuntimeError(result['message'])

    STATUS.parent.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps({'published':True,'quality':{'width':1080,'height':1350,'bytes':MEDIA.stat().st_size},'buffer_result':result,'media_url':RAW,'timestamp':time.time()},ensure_ascii=False,indent=2))
    subprocess.run(['git','add',str(STATUS)],check=True)
    subprocess.run(['git','commit','-m','Record HQ market tour publish result'],check=True)
    subprocess.run(['git','push'],check=True)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
