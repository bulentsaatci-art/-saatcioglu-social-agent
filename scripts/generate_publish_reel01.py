import json, os, math, time, wave, urllib.request, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

API_URL = 'https://api.buffer.com'
TARGET = 'saatcioglusupermarket'
REPO = 'bulentsaatci-art/-saatcioglu-social-agent'
MEDIA_PATH = 'public/reels/reel-01.mp4'
RAW_URL = f'https://raw.githubusercontent.com/{REPO}/main/{MEDIA_PATH}'
CAPTION = '''Mordoğan’da yazlığa geldin… İlk market alışverişinde sende ne eksik çıkar? ☀️\n\nSüt ürünleri mi, temizlik mi, içecekler mi, patili dostların mamaları mı?\n\nSizde ilk ne biter? Yorumlara tek kelime bırak 👇\n\n#Mordoğan #Karaburun #SaatçıoğluSupermarket #YazlıkHayatı'''


def gql(key, query):
    req = urllib.request.Request(API_URL, data=json.dumps({'query': query}).encode(), headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'}, method='POST')
    with urllib.request.urlopen(req, timeout=45) as r:
        p = json.loads(r.read().decode())
    if p.get('errors'): raise RuntimeError(json.dumps(p['errors'], ensure_ascii=False))
    return p['data']


def qs(v): return json.dumps(v, ensure_ascii=False)

def find_channel(key):
    d = gql(key, 'query { account { organizations { id name } } }')
    for org in d['account']['organizations']:
        c = gql(key, f'''query {{ channels(input: {{ organizationId: {qs(org['id'])} }}) {{ id name displayName service avatar isQueuePaused }} }}''')
        for ch in c['channels']:
            names = {str(ch.get('name','')).lower().replace('@',''), str(ch.get('displayName','')).lower().replace('@','')}
            if TARGET in names and ch.get('service') == 'instagram':
                if ch.get('isQueuePaused'): raise RuntimeError('Buffer Instagram queue is paused')
                return ch
    raise RuntimeError('Instagram channel not found')


def font(size, bold=True):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p, size)


def wrap(draw, text, f, maxw):
    lines=[]; cur=''
    for w in text.split():
        t=(cur+' '+w).strip()
        if draw.textbbox((0,0), t, font=f)[2] <= maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines


def draw_icon(d, kind, cx, cy, s, c):
    if kind == 'milk':
        d.rounded_rectangle((cx-s*.28,cy-s*.33,cx+s*.28,cy+s*.36),radius=int(s*.07),outline=c,width=5)
        d.polygon([(cx-s*.22,cy-s*.33),(cx-s*.10,cy-s*.52),(cx+s*.12,cy-s*.52),(cx+s*.23,cy-s*.33)],outline=c)
    elif kind == 'clean':
        d.polygon([(cx,cy-s*.48),(cx+s*.12,cy-s*.1),(cx+s*.48,cy),(cx+s*.12,cy+s*.1),(cx,cy+s*.48),(cx-s*.12,cy+s*.1),(cx-s*.48,cy),(cx-s*.12,cy-s*.1)],fill=c)
    elif kind == 'drink':
        d.rounded_rectangle((cx-s*.24,cy-s*.25,cx+s*.24,cy+s*.42),radius=int(s*.08),outline=c,width=5)
        d.rectangle((cx-s*.12,cy-s*.48,cx+s*.12,cy-s*.25),outline=c,width=5)
    elif kind == 'paw':
        d.ellipse((cx-s*.22,cy-s*.02,cx+s*.22,cy+s*.36),fill=c)
        for dx,dy,r in [(-.26,-.24,.12),(-.08,-.37,.11),(.11,-.37,.11),(.28,-.22,.12)]:
            d.ellipse((cx+s*(dx-r),cy+s*(dy-r),cx+s*(dx+r),cy+s*(dy+r)),fill=c)
    elif kind == 'bowl':
        d.arc((cx-s*.45,cy-s*.25,cx+s*.45,cy+s*.35),0,180,fill=c,width=6); d.line((cx-s*.4,cy+s*.05,cx+s*.4,cy+s*.05),fill=c,width=6)
    elif kind == 'comment':
        d.rounded_rectangle((cx-s*.46,cy-s*.34,cx+s*.46,cy+s*.26),radius=int(s*.14),outline=c,width=5); d.polygon([(cx-s*.12,cy+s*.26),(cx-s*.23,cy+s*.46),(cx+s*.02,cy+s*.26)],fill=c)
    else:
        d.ellipse((cx-s*.35,cy-s*.35,cx+s*.35,cy+s*.35),fill=(89,198,72)); d.line((cx-s*.12,cy+s*.18,cx+s*.22,cy-s*.18),fill=(255,255,255),width=6)


def generate_video(avatar_url):
    out = Path(MEDIA_PATH); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path('/tmp/reel01'); frames = tmp/'frames'; frames.mkdir(parents=True, exist_ok=True)
    logo_file = tmp/'avatar'; urllib.request.urlretrieve(avatar_url, logo_file)
    logo = Image.open(logo_file).convert('RGB')
    W,H,FPS=540,960,24
    GREEN=(89,198,72); DEEP=(30,111,58); DARK=(26,31,29); WHITE=(255,255,255); CREAM=(249,249,244)
    scenes=[
      (1.8,'Mordoğan’da yazlığa geldin…','İlk market alışverişinde sende ne eksik çıkar?','intro',(222,244,216)),
      (1.5,'Süt • Peynir • Kahvaltılık','Dolabı açınca ilk arananlar','milk',(228,246,222)),
      (1.5,'Temizlik Ürünleri','Yazlık açılınca sıra eve gelir','clean',(202,238,204)),
      (1.5,'Soğuk İçecekler','Mordoğan sıcağında dolap boş kalmasın','drink',(197,232,232)),
      (1.5,'Kedi • Köpek Mamaları','Patili dostları unutmak yok','paw',(228,246,222)),
      (1.5,'Bakliyat • Temel Gıda','Evde mutlaka olsun denilenler','bowl',(202,238,204)),
      (1.9,'Sizde ilk ne biter?','Yorumlara tek kelime bırak 👇','comment',(222,244,216)),
    ]
    logo.thumbnail((390,105))
    fi=0
    for si,(dur,title,sub,icon,bg) in enumerate(scenes):
        n=int(dur*FPS)
        for k in range(n):
            im=Image.new('RGB',(W,H),CREAM); d=ImageDraw.Draw(im)
            # soft background shapes
            d.ellipse((-90,120,170,380),fill=bg); d.ellipse((390,660,650,920),fill=bg)
            # logo card
            d.rounded_rectangle((55,38,485,155),radius=22,fill=WHITE)
            x=270-logo.width//2; y=96-logo.height//2; im.paste(logo,(x,y))
            d.rounded_rectangle((190,177,350,211),radius=17,fill=DEEP)
            tag='MORDOĞAN • İZMİR'; bb=d.textbbox((0,0),tag,font=font(13)); d.text((270-(bb[2]-bb[0])/2,184),tag,font=font(13),fill=WHITE)
            # icon
            d.ellipse((220,255,320,355),fill=WHITE,outline=DEEP,width=3); draw_icon(d,icon,270,305,58,DEEP)
            # card
            d.rounded_rectangle((42,390,498,665),radius=28,fill=WHITE,outline=(226,232,226),width=2)
            tf=font(34 if len(title)<28 else 29); yy=430
            for line in wrap(d,title,tf,390):
                bb=d.textbbox((0,0),line,font=tf); d.text((270-(bb[2]-bb[0])/2,yy),line,font=tf,fill=DARK); yy+=44
            yy+=18; sf=font(18,False)
            for line in wrap(d,sub,sf,390):
                bb=d.textbbox((0,0),line,font=sf); d.text((270-(bb[2]-bb[0])/2,yy),line,font=sf,fill=DEEP); yy+=27
            # footer
            d.rounded_rectangle((52,788,488,870),radius=25,fill=DARK)
            l1='YORUMLARA YAZ 👇' if si==6 else 'SAATÇIOĞLU SUPERMARKET'; bb=d.textbbox((0,0),l1,font=font(16)); d.text((270-(bb[2]-bb[0])/2,807),l1,font=font(16),fill=WHITE)
            l2='@saatcioglusupermarket'; bb=d.textbbox((0,0),l2,font=font(14,False)); d.text((270-(bb[2]-bb[0])/2,839),l2,font=font(14,False),fill=(205,220,205))
            # dots
            for j in range(len(scenes)):
                cx=170+j*34; r=7 if j==si else 4; d.ellipse((cx-r,913-r,cx+r,913+r),fill=DEEP if j<=si else (185,196,188))
            im.save(frames/f'f_{fi:05d}.jpg',quality=90); fi+=1
    # original light beat
    dur=sum(s[0] for s in scenes); sr=44100; wav=tmp/'beat.wav'
    with wave.open(str(wav),'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        vals=[]
        for i in range(int(dur*sr)):
            t=i/sr; beat=t%(60/116); env=max(0,1-beat/0.14); v=0.10*env*math.sin(2*math.pi*72*t)+0.018*math.sin(2*math.pi*220*t)
            vals.append(int(max(-1,min(1,v))*32767).to_bytes(2,'little',signed=True))
        wf.writeframes(b''.join(vals))
    silent=tmp/'silent.mp4'
    subprocess.run(['ffmpeg','-y','-framerate',str(FPS),'-i',str(frames/'f_%05d.jpg'),'-c:v','libx264','-preset','veryfast','-crf','29','-pix_fmt','yuv420p','-r',str(FPS),str(silent)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['ffmpeg','-y','-i',str(silent),'-i',str(wav),'-c:v','copy','-c:a','aac','-b:a','64k','-shortest','-movflags','+faststart',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def wait_public(url):
    for _ in range(20):
        try:
            req=urllib.request.Request(url,method='HEAD');
            with urllib.request.urlopen(req,timeout=15) as r:
                if r.status==200: return
        except Exception: pass
        time.sleep(3)
    raise RuntimeError('Generated video is not publicly reachable yet')


def publish(key, channel_id):
    q=f'''mutation PublishReel {{ createPost(input: {{ text: {qs(CAPTION)} channelId: {qs(channel_id)} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ video: {{ url: {qs(RAW_URL)} metadata: {{ thumbnailOffset: 1500 }} }} }}] metadata: {{ instagram: {{ type: reel shouldShareToFeed: true isAiGenerated: true }} }} }}) {{ ... on PostActionSuccess {{ post {{ id text status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    return gql(key,q)['createPost']


def main():
    key=os.environ['BUFFER_API_KEY']
    status=Path('status/published-reel-01.json')
    if status.exists():
        try:
            old=json.loads(status.read_text())
            if old.get('published'): print('Already published; exiting'); return
        except Exception: pass
    ch=find_channel(key)
    generate_video(ch['avatar'])
    subprocess.run(['git','config','user.name','Saatcioglu Social Agent'],check=True)
    subprocess.run(['git','config','user.email','actions@users.noreply.github.com'],check=True)
    subprocess.run(['git','add',MEDIA_PATH],check=True)
    subprocess.run(['git','commit','-m','Generate approved Reel 01 media'],check=True)
    subprocess.run(['git','push'],check=True)
    wait_public(RAW_URL)
    result=publish(key,ch['id'])
    if isinstance(result,dict) and result.get('message'): raise RuntimeError(result['message'])
    status.parent.mkdir(exist_ok=True)
    status.write_text(json.dumps({'published':True,'buffer_result':result,'media_url':RAW_URL,'timestamp':time.time()},ensure_ascii=False,indent=2))
    subprocess.run(['git','add',str(status)],check=True)
    subprocess.run(['git','commit','-m','Record Reel 01 publish result'],check=True)
    subprocess.run(['git','push'],check=True)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
