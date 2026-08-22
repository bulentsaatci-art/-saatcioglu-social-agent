import json
import os
import sys
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
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Buffer HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Buffer network error: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Buffer returned non-JSON response: {raw[:1000]}") from exc

    if payload.get("errors"):
        raise RuntimeError("Buffer GraphQL errors: " + json.dumps(payload["errors"], ensure_ascii=False))
    if "data" not in payload:
        raise RuntimeError("Buffer response missing data: " + json.dumps(payload, ensure_ascii=False))
    return payload["data"]


def gql_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def normalize(value):
    return str(value or "").strip().lower().replace("@", "")


def get_target_channel(api_key: str):
    data = graphql(
        api_key,
        """
        query GetOrganizations {
          account {
            organizations { id name }
          }
        }
        """,
    )
    organizations = data["account"]["organizations"]
    if not organizations:
        raise RuntimeError("Buffer organization bulunamadi")

    seen = []
    for org in organizations:
        org_id = org["id"]
        channels_data = graphql(
            api_key,
            f'''query GetChannels {{
              channels(input: {{ organizationId: {gql_string(org_id)} }}) {{
                id
                name
                displayName
                service
              }}
            }}''',
        )
        for channel in channels_data["channels"]:
            seen.append({
                "name": channel.get("name"),
                "displayName": channel.get("displayName"),
                "service": channel.get("service"),
            })
            names = {normalize(channel.get("name")), normalize(channel.get("displayName"))}
            if normalize(TARGET_CHANNEL_NAME) in names and normalize(channel.get("service")) == TARGET_SERVICE:
                print("Target channel found:", json.dumps(seen[-1], ensure_ascii=False))
                return channel

    raise RuntimeError(
        "Buffer'da hedef Instagram kanali bulunamadi. Gorulen kanallar: "
        + json.dumps(seen, ensure_ascii=False)
    )


def create_draft(api_key: str, channel_id: str, text: str, image_url: str | None = None):
    assets_block = ""
    if image_url:
        assets_block = f'''\n        assets: [{{ image: {{ url: {gql_string(image_url)} }} }}]'''

    mutation = f'''mutation CreateApprovedDraft {{
      createPost(input: {{
        text: {gql_string(text)}
        channelId: {gql_string(channel_id)}
        schedulingType: automatic
        mode: addToQueue
        saveToDraft: true
        aiAssisted: true{assets_block}
      }}) {{
        ... on PostActionSuccess {{
          post {{ id text status dueAt }}
        }}
        ... on MutationError {{ message }}
      }}
    }}'''
    return graphql(api_key, mutation)["createPost"]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Kullanim: send_to_buffer.py approved/file.json")

    api_key = os.environ.get("BUFFER_API_KEY")
    if not api_key:
        raise RuntimeError("BUFFER_API_KEY GitHub Secret bulunamadi")

    print("BUFFER_API_KEY secret detected (value hidden)")

    path = Path(sys.argv[1])
    item = json.loads(path.read_text(encoding="utf-8"))

    if item.get("approved") is not True:
        raise RuntimeError("Dosya approved:true degil; Buffer'a gonderilmeyecek")

    text = str(item.get("text", "")).strip()
    if not text:
        raise RuntimeError("Paylasim metni bos")

    if item.get("saveToDraft", True) is not True:
        raise RuntimeError("V1 guvenlik kilidi: saveToDraft true olmak zorunda")

    image_url = str(item.get("image_url", "")).strip() or None
    if TARGET_SERVICE == "instagram" and not image_url:
        raise RuntimeError("Instagram taslagi icin image_url veya video asset gerekli")

    channel = get_target_channel(api_key)
    result = create_draft(api_key, channel["id"], text, image_url)
    print("Buffer result:", json.dumps(result, ensure_ascii=False, indent=2))

    if isinstance(result, dict) and result.get("message"):
        raise RuntimeError("Buffer createPost error: " + result["message"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        raise
