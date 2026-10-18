# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems in the PopNow API or in this repository.

- Email **support@popnow.ai** with the subject line "Security", or use the form at <https://popnow.ai/contact>.
- Alternatively, open a [private security advisory](https://github.com/popnow-ai/popnow-api/security/advisories/new) on GitHub.

Include what you found, how to reproduce it, and any `request_id` values involved. **Never include a live API key**; if you believe a key has leaked, revoke it in the [API console](https://popnow.ai/api/console/keys) first.

We will acknowledge your report, keep you informed while we investigate, and credit you if you wish once a fix is out.

## Scope

- The PopNow API at `https://api.popnow.ai`, its webhooks and the MCP server at `https://api.popnow.ai/mcp`.
- The example code in this repository (for example, a flaw in the webhook signature checks).
