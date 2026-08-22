import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.buffer.com"
TARGET_CHANNEL_NAME = "saatcioglusupermarket"
TARGET_SERVICE = "instagram"


def graphql(api_key: str, query: str):
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Buffer HTTP {exc.code}: {body}") from exc
    payload = json.loads(raw)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def normalize(value):
    return str(value or "").strip().lower().replace("@", "")


def find_channel(api_key: str):
    account = graphql(api_key, "query { account { organizations { id name } } }")
    for org in account["account"]["organizations"]:
        org_id = org["id"]
        data = graphql(api_key, f'''query {{
          channels(input: {{ organizationId: {q(org_id)} }}) {{
            id name displayName service
          }}
        }}''')
        for ch in data["channels"]:
            names = {normalize(ch.get("name")), normalize(ch.get("displayName"))}
            if normalize(TARGET_CHANNEL_NAME) in names and normalize(ch.get("service")) == TARGET_SERVICE:
                return org_id, ch
    raise RuntimeError("Target Instagram channel not found")


def main():
    api_key = os.environ.get("BUFFER_API_KEY")
    if not api_key:
        raise RuntimeError("BUFFER_API_KEY secret missing")

    org_id, channel = find_channel(api_key)
    data = graphql(api_key, f'''query FeedSnapshot {{
      posts(
        first: 50
        input: {{
          organizationId: {q(org_id)}
          filter: {{ status: [sent], channelIds: [{q(channel['id'])}] }}
          sort: [{{ field: createdAt, direction: desc }}]
        }}
      ) {{
        edges {{
          node {{
            id
            text
            status
            createdAt
            dueAt
            assets {{ id mimeType source thumbnail type }}
            metadata {{ type }}
          }}
        }}
        pageInfo {{ hasNextPage endCursor }}
      }}
    }}''')

    posts = [edge["node"] for edge in data["posts"]["edges"]]
    out = {
        "channel": channel,
        "count": len(posts),
        "posts": posts,
        "pageInfo": data["posts"]["pageInfo"],
    }
    Path("status").mkdir(exist_ok=True)
    Path("status/feed-snapshot.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Fetched {len(posts)} sent/native posts")


if __name__ == "__main__":
    main()
