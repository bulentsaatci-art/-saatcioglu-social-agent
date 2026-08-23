import io, json, os, time, urllib.request
from pathlib import Path
from PIL import Image

API_URL = 'https://api.buffer.com'
TARGET = 'saatcioglusupermarket'
THUMB = 'https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Fd493698e-32fa-4bd7-82d4-85112c1b83c9/watermark:F/width:160?csig=AAAAAAAAAAAAAAAAAAAAAAPp5zihkIoX2TRNxuLf4pm30xFzek-Xp4Zlm94SeoqO&exp=1787485542&osig=AAAAAAAAAAAAAAAAAAAAAHcNnrM8-wQ4vq_DicDCjNo2KpLeCh14xR6_rqvT_ORP&signer=media-rpc&x-canva-quality=thumbnail'
CAPTION = '''Mordoğan’da bugün kısa bir market turu 👀\n\nSüt & peynir, atıştırmalıklar, temizlik ve ev ihtiyaçları…\n\nBir sonraki turda hangi reyonu görmek istersiniz? Yorumlara yazın 👇\n\n#Mordoğan #Karaburun #SaatçıoğluSupermarket'''


def gql(key, query):
    req = urllib.request.Request(API_URL, data=json.dumps({'query': query}).encode(), headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'}, method='POST')
    with urllib.request.urlopen(req, timeout=45) as r:
        p=json.loads(r.read().decode())
    if p.get('errors'): raise RuntimeError(json.dumps(p['errors'], ensure_ascii=False))
    return p['data']

def qs(v): return json.dumps(v, ensure_ascii=False)

def find_channel(key):
    d=gql(key,'query { account { organizations { id name } } }')
    for org in d['account']['organizations']:
        c=gql(key,f'''query {{ channels(input: {{ organizationId: {qs(org['id'])} }}) {{ id name displayName service isQueuePaused }} }}''')
        for ch in c['channels']:
            names={str(ch.get('name','')).lower().replace('@',''),str(ch.get('displayName','')).lower().replace('@','')}
            if TARGET in names and ch.get('service')=='instagram':
                if ch.get('isQueuePaused'): raise RuntimeError('Buffer Instagram queue is paused')
                return ch
    raise RuntimeError('Instagram channel not found')

def candidates():
    yield THUMB
    yield THUMB.replace('height:200','height:1350').replace('width:160','width:1080').replace('x-canva-quality=thumbnail','x-canva-quality=print')
    yield THUMB.replace('height:200','height:1350').replace('width:160','width:1080')
    base='https://media.canva.com/v2/image-resize/format:PNG/height:1350/quality:100/uri:ifs%3A%2F%2FM%2Fd493698e-32fa-4bd7-82d4-85112c1b83c9/watermark:F/width:1080'
    yield base

def validate_url(url):
    try:
        req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data=r.read()
            ctype=r.headers.get('content-type','')
        im=Image.open(io.BytesIO(data)); im.load()
        return {'ok': im.width>=1080 and im.height>=1350, 'width':im.width,'height':im.height,'bytes':len(data),'content_type':ctype}
    except Exception as e:
        return {'ok':False,'error':repr(e)}

def publish(key, channel_id, media_url):
    q=f'''mutation PublishHQ {{ createPost(input: {{ text: {qs(CAPTION)} channelId: {qs(channel_id)} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ image: {{ url: {qs(media_url)} }} }}] metadata: {{ instagram: {{ type: post shouldShareToFeed: true isAiGenerated: false }} }} }}) {{ ... on PostActionSuccess {{ post {{ id text status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    return gql(key,q)['createPost']

def main():
    key=os.environ['BUFFER_API_KEY']
    checks=[]; chosen=None
    for u in candidates():
        r=validate_url(u); checks.append({'url':u,'check':r})
        if r.get('ok'):
            chosen=u; break
    status=Path('status/published-hq-market-tour.json'); status.parent.mkdir(exist_ok=True)
    if not chosen:
        status.write_text(json.dumps({'published':False,'reason':'No Canva URL passed 1080x1350 quality gate','checks':checks,'timestamp':time.time()},ensure_ascii=False,indent=2))
        raise RuntimeError('No Canva URL passed 1080x1350 quality gate')
    ch=find_channel(key)
    result=publish(key,ch['id'],chosen)
    if isinstance(result,dict) and result.get('message'):
        status.write_text(json.dumps({'published':False,'reason':result['message'],'checks':checks,'timestamp':time.time()},ensure_ascii=False,indent=2))
        raise RuntimeError(result['message'])
    status.write_text(json.dumps({'published':True,'chosen_media_url':chosen,'checks':checks,'buffer_result':result,'timestamp':time.time()},ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
