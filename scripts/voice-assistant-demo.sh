#!/usr/bin/env bash
# Proves the Korean voice-assistant path end to end: speech -> Whisper STT
# (speaches) -> Open WebUI -> gateway -> Ollama -> Korean response. Requires
# the docker-compose stack (`make up`) running with a local `ollama serve`
# reachable from Docker Desktop, and macOS `say`/`afconvert` to synthesize a
# Korean test clip (swap in a real recording with AUDIO_FILE=/path/to.wav).
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3001}"
SPEACHES_URL="${SPEACHES_URL:-http://localhost:8000}"
STT_MODEL="${STT_MODEL:-Systran/faster-whisper-small}"
CHAT_MODEL="${CHAT_MODEL:-qwen3:8b}"
DEMO_EMAIL="${DEMO_EMAIL:-demo@example.com}"
DEMO_PASSWORD="${DEMO_PASSWORD:-demo1234}"
AUDIO_FILE="${AUDIO_FILE:-}"

cd "$(dirname "$0")/.."

if [ -z "$AUDIO_FILE" ]; then
  AUDIO_FILE="$(mktemp -t voice-demo).wav"
  say -v Yuna "요청 추적의 장점 한 가지를 설명해 주세요." -o "${AUDIO_FILE%.wav}.aiff"
  afconvert -f WAVE -d LEI16 "${AUDIO_FILE%.wav}.aiff" "$AUDIO_FILE"
  echo "==> Synthesized Korean test clip at $AUDIO_FILE"
fi

echo "==> Ensuring $STT_MODEL is downloaded in speaches"
curl -sf -m 300 -X POST "$SPEACHES_URL/v1/models/$STT_MODEL" >/dev/null || true

echo "==> Ensuring an Open WebUI admin account exists"
SIGNIN=$(curl -s -m 10 -X POST "$BASE_URL/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$DEMO_EMAIL\",\"password\":\"$DEMO_PASSWORD\"}")
TOKEN=$(echo "$SIGNIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

if [ -z "$TOKEN" ]; then
  SIGNUP=$(curl -s -m 10 -X POST "$BASE_URL/api/v1/auths/signup" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"demo\",\"email\":\"$DEMO_EMAIL\",\"password\":\"$DEMO_PASSWORD\"}")
  TOKEN=$(echo "$SIGNUP" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
fi

echo "==> Pointing Open WebUI's STT model at $STT_MODEL"
CONFIG=$(curl -s -m 10 "$BASE_URL/api/v1/audio/config" -H "Authorization: Bearer $TOKEN")
echo "$CONFIG" | python3 -c "
import json, sys
cfg = json.load(sys.stdin)
cfg['stt']['MODEL'] = '$STT_MODEL'
print(json.dumps(cfg))
" > /tmp/voice-demo-audio-config.json
curl -s -m 10 -X POST "$BASE_URL/api/v1/audio/config/update" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary @/tmp/voice-demo-audio-config.json >/dev/null

echo "==> Transcribing Korean audio via Open WebUI -> speaches"
TRANSCRIPT=$(curl -s -m 60 -X POST "$BASE_URL/api/v1/audio/transcriptions" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${AUDIO_FILE};type=audio/wav;filename=clip.wav" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['text'])")
echo "    Transcript: $TRANSCRIPT"

echo "==> Sending the transcript through Open WebUI -> gateway -> Ollama"
PAYLOAD=$(CHAT_MODEL="$CHAT_MODEL" TRANSCRIPT="$TRANSCRIPT" python3 -c "
import json, os
print(json.dumps({
    'model': os.environ['CHAT_MODEL'],
    'messages': [{'role': 'user', 'content': os.environ['TRANSCRIPT']}],
    'stream': False,
}))
")
curl -s -m 60 -X POST "$BASE_URL/api/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  | python3 -c "import sys,json; print('    Response:', json.load(sys.stdin)['choices'][0]['message']['content'])"

echo "==> Done. Open $BASE_URL in a browser to drive the same flow by voice (mic icon in the chat box)."
