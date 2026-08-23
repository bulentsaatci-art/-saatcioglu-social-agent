import json, os, time, urllib.request, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

API='https://api.buffer.com'
TARGET='saatcioglusupermarket'
REPO='bulentsaatci-art/-saatcioglu-social-agent'
MEDIA='public/posts/kosedere-uzum-senligi-2026.jpg'
RAW=f'https://raw.githubusercontent.com/{REPO}/main/{MEDIA}'
STATUS=Path('status/published-kosedere-2026.json')
CAPTION='''Bugün komşumuz Kösedere’de üzümün, emeğin ve dayanışmanın güzel buluşması var. 🍇\n\n17. Kösedere Üzüm Şenliği 22–23 Ağustos’ta devam ediyor. Katılan herkese keyifli bir gün dileriz. 💚\n\nMordoğan’dan Kösedere’ye selam!\n\n#KösedereÜzümŞenliği #Kösedere #Karaburun #Mordoğan #SaatçıoğluSupermarket'''

def qs(v): return json.dumps(v,ensure_ascii=False)
def gql(key,q):
    req=urllib.request.Request(API,data=json.dumps({'query':q}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r: p=json.loads(r.read().decode())
    if p.get('errors'): raise RuntimeError(json.dumps(p['errors'],ensure_ascii=False))
    return p['data']

def channel(key):
    a=gql(key,'query { account { organizations { id } } }')
    for o in a['account']['organizations']:
        d=gql(key,f'''query {{ channels(input: {{ organizationId: {qs(o['id'])} }}) {{ id name displayName service avatar isQueuePaused }} }}''')
        for c in d['channels']:
            names={str(c.get('name','')).lower().replace('@',''),str(c.get('displayName','')).lower().replace('@','')}
            if TARGET in names and c.get('service')=='instagram':
                if c.get('isQueuePaused'): raise RuntimeError('Buffer queue paused')
                return c
    raise RuntimeError('Instagram channel not found')

def font(n,b=True):
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if b else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p,n)

def poster(avatar):
    out=Path(MEDIA); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path('/tmp/kosedere-avatar'); urllib.request.urlretrieve(avatar,tmp)
    logo=Image.open(tmp).convert('RGB'); logo.thumbnail((780,170))
    W,H=1080,1350; BG=(249,247,238); GR=(49,113,59); DG=(26,70,38); PUR=(113,55,129); WHITE=(255,255,255)
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
    d.ellipse((-180,850,460,1490),fill=(229,238,213)); d.ellipse((760,-140,1210,310),fill=(235,223,240))
    # grape clusters
    for ox,oy,scale in [(120,260,1.0),(865,760,.85)]:
        pts=[(0,0),(55,-18),(105,8),(28,55),(82,62),(130,72),(12,112),(70,116),(116,128)]
        for px,py in pts:
            r=int(34*scale); x=int(ox+px*scale); y=int(oy+py*scale); d.ellipse((x-r,y-r,x+r,y+r),fill=PUR)
        d.line((ox+40*scale,oy-62*scale,ox+52*scale,oy-20*scale),fill=GR,width=max(3,int(9*scale)))
        d.ellipse((ox-8*scale,oy-90*scale,ox+82*scale,oy-38*scale),fill=(96,153,77))
    d.rounded_rectangle((95,70,985,250),radius=42,fill=WHITE)
    im.paste(logo,(W//2-logo.width//2,160-logo.height//2))
    tag='MORDOĞAN • KARABURUN'; f=font(30); bb=d.textbbox((0,0),tag,font=f); d.rounded_rectangle((W//2-(bb[2]-bb[0])/2-32,300,W//2+(bb[2]-bb[0])/2+32,366),radius=30,fill=GR); d.text((W//2-(bb[2]-bb[0])/2,313),tag,font=f,fill=WHITE)
    d.text((95,435),'BUGÜN KÖSEDERE’DE',font=font(53),fill=DG)
    d.text((95,515),'17. ÜZÜM',font=font(95),fill=PUR)
    d.text((95,620),'ŞENLİĞİ 🍇',font=font(95),fill=PUR)
    d.text((98,760),'22–23 AĞUSTOS 2026',font=font(43),fill=GR)
    msg=['Üzümün bereketi, üreticinin emeği','ve Kösedere’nin güzel geleneğiyle…','Katılan herkese keyifli bir gün dileriz.']
    y=855
    for line in msg:
        d.text((98,y),line,font=font(33,False),fill=DG); y+=54
    d.rounded_rectangle((90,1120,990,1265),radius=42,fill=DG)
    t1='SAATÇIOĞLU SUPERMARKET'; t2='Mordoğan’dan Kösedere’ye selam 💚'
    b=d.textbbox((0,0),t1,font=font(39)); d.text((W//2-(b[2]-b[0])/2,1150),t1,font=font(39),fill=WHITE)
    b=d.textbbox((0,0),t2,font=font(28,False)); d.text((W//2-(b[2]-b[0])/2,1205),t2,font=font(28,False),fill=(220,238,220))
    im.save(out,quality=92,optimize=True)

def wait(url):
    for _ in range(20):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=15) as r:
                if r.status==200:return
        except Exception: pass
        time.sleep(3)
    raise RuntimeError('media not public')

def publish(key,cid):
    q=f'''mutation {{ createPost(input: {{ text: {qs(CAPTION)} channelId: {qs(cid)} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ image: {{ url: {qs(RAW)} }} }}] metadata: {{ instagram: {{ type: post shouldShareToFeed: true isAiGenerated: true }} }} }}) {{ ... on PostActionSuccess {{ post {{ id status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    return gql(key,q)['createPost']

def main():
    if STATUS.exists():
        try:
            if json.loads(STATUS.read_text()).get('published'): print('Already published'); return
        except Exception: pass
    key=os.environ['BUFFER_API_KEY']; ch=channel(key); poster(ch['avatar'])
    subprocess.run(['git','config','user.name','Saatcioglu Social Agent'],check=True); subprocess.run(['git','config','user.email','actions@users.noreply.github.com'],check=True)
    subprocess.run(['git','add',MEDIA],check=True); subprocess.run(['git','commit','-m','Create Kosedere festival community post'],check=True); subprocess.run(['git','push'],check=True); wait(RAW)
    result=publish(key,ch['id'])
    if isinstance(result,dict) and result.get('message'): raise RuntimeError(result['message'])
    STATUS.parent.mkdir(exist_ok=True); STATUS.write_text(json.dumps({'published':True,'buffer_result':result,'media_url':RAW,'timestamp':time.time()},ensure_ascii=False,indent=2))
    subprocess.run(['git','add',str(STATUS)],check=True); subprocess.run(['git','commit','-m','Record Kosedere post publish result'],check=True); subprocess.run(['git','push'],check=True)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
