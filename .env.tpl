# Render: op inject -i .env.tpl -o .env   (TODO-voyage item does not exist yet; create in 1Password first)
ANTHROPIC_API_KEY={{ op://homelab-ai/anthropic-ai3-fullstack/api-key }}
VOYAGE_API_KEY={{ op://homelab-ai/TODO-voyage-api-key/credential }}
PHOENIX_API_KEY={{ op://homelab-apps/phoenix/api-key-observability }}
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
PHOENIX_PROJECT_NAME=ai3-your-handle
