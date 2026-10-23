# Agent instructions

See CLAUDE.md for project context.

## Secrets

1Password (account `tkhllc`) is the only source of truth for secrets. This repo reads: homelab-ai, homelab-apps (see .env.tpl).

- Local dev: `op inject -i .env.tpl -o .env` (rendered `.env` is gitignored, mode 600).
- One-offs: `op run --env-file .env.tpl -- <cmd>`.
- Never hand-write a secret value into a file, chat or argv. Create the 1Password item first, then reference it as `op://<vault>/<item>/<field>` in `.env.tpl`.
- On homelab hosts the `op-render` manifest owns the rendered file.
- Before committing: `gitleaks detect --no-git --redact --source .` must report 0.
- Convention: homelab-main `docs/security/secrets-management-1password.md`.
