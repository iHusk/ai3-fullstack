# Render: op inject -i .env.tpl -o .env   (TODO-* items do not exist yet; create in 1Password first)
ANTHROPIC_API_KEY={{ op://homelab-ai/TODO-anthropic-api-key/credential }}
VOYAGE_API_KEY={{ op://homelab-ai/TODO-voyage-api-key/credential }}
PHOENIX_API_KEY={{ op://homelab-apps/TODO-phoenix-api-key/credential }}
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
PHOENIX_PROJECT_NAME=ai3-your-handle
