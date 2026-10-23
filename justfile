# Secrets guardrail
check-secrets:
    gitleaks detect --no-git --redact --source .
