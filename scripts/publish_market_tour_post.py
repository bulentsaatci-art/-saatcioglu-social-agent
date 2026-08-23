import json, os, time, urllib.request
from pathlib import Path

API_URL='https://api.buffer.com'
TARGET='saatcioglusupermarket'
IMAGE_URL='https://media.canva.com/v2/document-image/hash:726209384/height:500/id:DAHTFgvxJes/type:B/width:400?brand=BAEPZj8PZP8&csig=AAAAAAAAAAAAAAAAAAAAAOOpnYk5dc6TkjtvZRBW2vZAOJz25fzdliTvuDPv61qG&disableexport=T&exp=1787471987&fallback=https%3A%2F%2Fs3.amazonaws.com%2Fdocument-export.canva.com%2FvxJes%2FDAHTFgvxJes%2F1%2Fthumbnail%2F0001.png%3FX-Amz-Algorithm%3DAWS4-HMAC-SHA256%26X-Amz-Credential%3DAKIAQYCGKMUHYGFFNMW3%252F20260822%252Fus-east-1%252Fs3%252Faws4_request%26X-Amz-Date%3D20260822T112106Z%26X-Amz-Expires%3D74321%26X-Amz-Signature%3Db6b1430d2bd52971b33c39331773fba4c0a0146e73cf24bf9526d89cede62eb6%26X-Amz-SignedHeaders%3Dhost%26response-expires%3DSun%252C%252023%2520Aug%25202026%252007%253A59%253A47%2520GMT&osig=AAAAAAAAAAAAAAAAAAAAAK9UXZoJyF-Jq__xfnV0DRvaAS96IKEUyHr9bLURIj7U&page=1&signed=brand%2Cdisableexport%2Cfallback%2Cpage%2Cversion&signer=document-rpc&version=1'
CAPTION='''Mordoğan’da bugün kısa bir market turu 👀\n\nSüt & peynir, atıştırmalıklar, temizlik ve ev ihtiyaçları…\n\nBir sonraki turda hangi reyonu görmek istersiniz? Yorumlara yazın 👇\n\n#Mordoğan #Karaburun #SaatçıoğluSupermarket #MordoğanMarket'''


def gql(key, query):
    req=urllib.request.Request(API_URL,data=json.dumps({'query':query}).encode('utf-8'),headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r:
        payload=json.loads(r.read().decode('utf-8'))
    if payload.get('errors'):
        raise RuntimeError(json.dumps(payload['errors'],ensure_ascii=False))
    return payload['data']

def q(v): return json.dumps(v,ensure_ascii=False)

def find_channel(key):
    d=gql(key,'query { account { organizations { id } } }')
    for org in d['account']['organizations']:
        c=gql(key,f'''query {{ channels(input: {{ organizationId: {q(org['id'])} }}) {{ id name displayName service isQueuePaused }} }}''')
        for ch in c['channels']:
            names={str(ch.get('name','')).lower().replace('@',''),str(ch.get('displayName','')).lower().replace('@','')}
            if TARGET in names and ch.get('service')=='instagram':
                if ch.get('isQueuePaused'): raise RuntimeError('Buffer Instagram queue is paused')
                return ch
    raise RuntimeError('Instagram channel not found')

def main():
    key=os.environ['BUFFER_API_KEY']
    ch=find_channel(key)
    mutation=f'''mutation PublishMarketTour {{ createPost(input: {{ text: {q(CAPTION)} channelId: {q(ch['id'])} schedulingType: automatic mode: shareNow aiAssisted: true assets: [{{ image: {{ url: {q(IMAGE_URL)} }} }}] metadata: {{ instagram: {{ type: post }} }} }}) {{ ... on PostActionSuccess {{ post {{ id text status sentAt externalLink sharedNow shareMode }} }} ... on MutationError {{ message }} }} }}'''
    result=gql(key,mutation)['createPost']
    if isinstance(result,dict) and result.get('message'): raise RuntimeError(result['message'])
    status=Path('status/published-market-tour-post.json'); status.parent.mkdir(exist_ok=True)
    status.write_text(json.dumps({'published':True,'buffer_result':result,'image_url':IMAGE_URL,'timestamp':time.time()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
