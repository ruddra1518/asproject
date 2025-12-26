# Environment setup

1. Copy the example file and fill in real values:

```bash
cp .env.example .env
# then edit .env and paste your Cosmos endpoint and key
```

2. Install dependency:

```bash
pip install azure-cosmos
```

3. Confirm `COSMOS_ENDPOINT` and `COSMOS_KEY` are set in `.env` before starting your app.

Note: `.env` is ignored by git via `.gitignore`. Commit only `.env.example`.
