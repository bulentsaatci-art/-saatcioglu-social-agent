import json, os, time, urllib.request, urllib.parse
from io import BytesIO
from pathlib import Path
from PIL import Image

API_URL='https://api.buffer.com'
TARGET='saatcioglusupermarket'
REPO='bulentsaatci-art/-saatcioglu-social-agent'
SVG_RAW=f'https://raw.githubusercontent.com/{REPO}/main/public/posts/market-tour-hq-20260823.svg'
MEDIA_URL='https://images.weserv.nl/?url='+urllib.parse.quote(SVG_RAW,safe='')+'&w=1080&h=1350&fit=cover&output=jpg&q=95'
CAPTION='''Mordoğan’da bugün kısa bir market turu 👀\n\nSüt & peynir, atıştırmalıklar, temizlik ve ev ihtiyaçları…\n\nBir sonraki turda hangi reyonu görmek istersiniz?\nYorumlara yazın 👇\n\n#Mordoğan #Karaburun #SaatçıoğluSupermarket'''
STATUS=Path('status/published-hq-market-tour-v2.json')

def qs(v): return json.dumps(v,ensure_ascii=False)

def gql(key,query):
    req=urllib.request.Request(API_URL,data=json.dumps({'query':query}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r: payload=json.loads(r.read().decode())
    if payload.get('errors'): raise RuntimeError(json.dumps(payload['errors'],ensure_ascii=False))
    return payload['data']

def find_channel(key):
    orgs=gql(key,'query { account { organizations { id name } } }')['account']['organizations']
    for org in orgs:
        data=gql(key,f'''query {{ channels(input: {{ organizationId: {qs(org['id'])} }}) {{ id name displayName service isQueuePaused }} }}''')
        for ch in data['channels']:
            names={str(ch.get('name','')).lower().replace('@',''),str(ch.get('displayName','')).lower().replace('@','')}
            if TARGET in names and ch.get('service')=='instagram':
                if ch.get('isQueuePaused'): raise RuntimeError('Buffer Instagram queue is paused')
                return ch
    raise RuntimeError('Instagram channel not found')

def quality_gate():
    req=urllib.request.Request(MEDIA_URL,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        body=r.read(); ctype=r.headers.get('Content-Type','')
    im=Image.open(BytesIO(body)); im.load()
    w,h=im.size
    ok=(w==1080 and h==1350 and len(body)>=150000 and ('image/' in ctype or im.format in ('JPEG','PNG','WEBP')))
    result={'ok':ok,'width':w,'height':h,'bytes':len(body),'format':im.format,'content_type':ctype,'media_url':MEDIA_URL}
    if not ok: raise RuntimeError('QUALITY_GATE_FAILED '+json.dumps(result,ensure_ascii=False))
    return result

def publish(key,channel_id):
    query=f'''mutation PublishHQ {{ createPost(input: {{ text: {qs(CAPTION)} channelId: {qs(channel_id)} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ image: {{ url: {qs(MEDIA_URL)} }} }}] metadata: {{ instagram: {{ type: post shouldShareToFeed: true isAiGenerated: true }} }} }}) {{ ... on PostActionSuccess {{ post {{ id text status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    return gql(key,query)['createPost']

def git_save():
    import subprocess
    subprocess.run(['git','config','user.name','Saatcioglu Social Agent'],check=True)
    subprocess.run(['git','config','user.email','actions@users.noreply.github.com'],check=True)
    subprocess.run(['git','add',str(STATUS)],check=True)
    subprocess.run(['git','commit','-m','Record HQ market tour publish result'],check=True)
    subprocess.run(['git','pull','--rebase'],check=True)
    subprocess.run(['git','push'],check=True)

def main():
    key=os.environ['BUFFER_API_KEY']
    if STATUS.exists():
        try:
            old=json.loads(STATUS.read_text())
            if old.get('published') and old.get('buffer_result',{}).get('post',{}).get('status')=='sent':
                print('Already published'); return
        except Exception: pass
    record={'published':False,'timestamp':time.time(),'source_svg':SVG_RAW,'media_url':MEDIA_URL}
    try:
        record['quality_gate']=quality_gate()
        ch=find_channel(key); record['channel']={'id':ch['id'],'name':ch.get('name'),'displayName':ch.get('displayName')}
        result=publish(key,ch['id']); record['buffer_result']=result
        if isinstance(result,dict) and result.get('message'): raise RuntimeError(result['message'])
        post=(result or {}).get('post') or {}
        record['published']=(post.get('status')=='sent' and bool(post.get('externalLink')))
        if not record['published']: raise RuntimeError('Buffer did not confirm sent + externalLink: '+json.dumps(result,ensure_ascii=False))
    except Exception as e:
        record['error']=repr(e)
    STATUS.parent.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    git_save()
    print(json.dumps(record,ensure_ascii=False,indent=2))
    if not record.get('published'): raise SystemExit(1)

if __name__=='__main__': main()
