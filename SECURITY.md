# Security

- Never open issues that paste live API keys, cookies, or `.env` values.
- This project is a **policy kernel**, not a hosted scanner.
- If you find a way a model can keep posting `/scan` after HTTP 503 `busy`
  (tight-loop retry, a hammer MCP tool, client timeout shorter than the
  worker), file a private advisory if the GitHub repo has them enabled;
  otherwise an issue with a **redacted** repro.

Do not ask maintainers to add an `occupancy_retry` / hammer-busy MCP tool
“just for debugging.” Occupancy is a lock. Retrying it livelocks the holder.
