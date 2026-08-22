import json
import os
import sys
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
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def gql_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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

    for org in organizations:
        org_id = org["id"]
        channels_data = graphql(
            api_key,
            f'''query GetChannels {{
              channels(input: {{ organizationId: {gql_string(org_id)} }}) {{
                id
                name
                service
              }}
            }}''',
        )
        for channel in channels_data["channels"]:
            if (
                channel.get("name", "").lower() == TARGET_CHANNEL_NAME.lower()
                and channel.get("service", "").lower() == TARGET_SERVICE
            ):
                return channel
    raise RuntimeError(
        f"Buffer'da {TARGET_SERVICE}/{TARGET_CHANNEL_NAME} kanali bulunamadi"
    )


def create_draft(api_key: str, channel_id: str, text: str):
    mutation = f'''mutation CreateApprovedDraft {{
      createPost(input: {{
        text: {gql_string(text)}
        channelId: {gql_string(channel_id)}
        schedulingType: automatic
        mode: addToQueue
        saveToDraft: true
        aiAssisted: true
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

    path = Path(sys.argv[1])
    item = json.loads(path.read_text(encoding="utf-8"))

    if item.get("approved") is not True:
        raise RuntimeError("Dosya approved:true degil; Buffer'a gonderilmeyecek")

    text = str(item.get("text", "")).strip()
    if not text:
        raise RuntimeError("Paylasim metni bos")

    if item.get("saveToDraft", True) is not True:
        raise RuntimeError("V1 guvenlik kilidi: saveToDraft true olmak zorunda")

    channel = get_target_channel(api_key)
    result = create_draft(api_key, channel["id"], text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("message"):
        raise RuntimeError(result["message"])


if __name__ == "__main__":
    main()
