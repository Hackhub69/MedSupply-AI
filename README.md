# MedSupply AI

**Predict shortages. Reduce waste. Get medicines where they’re needed.**

MedSupply AI is a healthcare logistics prototype that helps a hospital network explore medicine shortages, expiry risks, and possible stock transfers. The demo uses **synthetic data** and requires a qualified person to review every recommendation.

> **Prototype status:** The IBM Db2 connection is implemented but has not been validated against a live Db2 instance. LangChain document retrieval currently uses an in-memory vector store, not Db2 vector search. This is not a clinical or operational system.

## What it does

- **Inventory monitoring:** highlights estimated coverage below 14 days and batches expiring within 30 days.
- **Demand estimation:** uses a transparent 28-day average to calculate days of supply.
- **Transfer suggestions:** identifies potential donors while reserving 30 days of demand at the sending facility; suggestions do not execute transfers.
- **Demand surge simulator:** compares coverage and proposed transfers under hypothetical demand changes without changing records.
- **Guidance retrieval:** uses LangChain with local deterministic token embeddings to find relevant sample document excerpts.
- **Workspace:** summarizes hospitals, medicines, suppliers and alerts, with links to filtered inventory.
- **Accessible controls:** responsive layout, search, risk filters and a saved light/dark preference.

## Try it locally

Requirements: Python 3.10 or newer and pip.

```bash
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install and run:

```bash
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**. The app creates `demo.db` with synthetic records on first launch. To recreate the sample data relative to the current date, run `python reset_demo.py`. This deletes the existing local demo database and its changes.

## IBM Db2 setup

1. Install the optional driver with `pip install -r requirements-db2.txt`.
2. Run `python generate_db2_seed.py` to generate `db2_seed.sql`. Review it, then run it using your Db2 client **only in a new, empty schema**. It creates six tables and inserts synthetic records; generating the file does not connect to Db2.
3. Configure your connection's current schema, then set `DB2_CONNECTION_STRING` to your Db2 connection details. For example, in PowerShell:

   ```powershell
   $env:DB2_CONNECTION_STRING = 'DATABASE=yourdb;HOSTNAME=yourhost;PORT=50000;PROTOCOL=TCPIP;UID=youruser;PWD=yourpassword;SECURITY=SSL;'
   python app.py
   ```

Keep credentials out of source control. Connection and TLS settings depend on your Db2 deployment. The Db2 path and generated SQL require validation with an actual instance. If deploying with Db2, ensure the optional native `ibm-db` driver is installed in the target runtime; the default Vercel configuration is intended for the sample-data demo.

## Architecture

```text
Browser → Flask dashboard and scenario API
              ├─ Inventory monitor + 28-day demand estimate
              ├─ Transfer recommendation rules
              ├─ LangChain in-memory guidance retrieval
              └─ IBM Db2 (configured) OR local SQLite sample database
```

The app reads hospitals, medicines, batches, daily demand, suppliers, and documents from the selected database. The demand calculation includes missing days as zero. A position without usable demand has no coverage forecast. Transfers are limited by donor surplus and batches expiring within 14 days are excluded from transferable stock. Allocation is a prototype estimate, not a batch-level transfer plan.

## Vercel deployment

Vercel detects the Flask `app.py` entry point. Without Db2 credentials, the hosted demo creates an ephemeral SQLite database under `/tmp`; it contains synthetic data and may be recreated when a serverless instance restarts. Do not use it for durable records. See [Vercel's Flask documentation](https://vercel.com/docs/frameworks/backend/flask) for platform details.

## Tests and demo

```bash
python -m unittest -v
```

The checks cover dashboard rendering, scenario validation and read-only behavior, and the donor reserve rule. See [DEMO.md](DEMO.md) for a suggested walkthrough.

## Limitations and responsible use

The forecast is a simple average, not a validated clinical forecasting model. The prototype does not account for substitutions, actual batch allocation, reserved stock, transit time, cold-chain logistics, uncertain supplier lead times, access controls, or audit history. A qualified reviewer must verify every recommendation. No clinical, financial, or waste-reduction impact has been measured.

## Db2Hack submission checklist

- Validate a working Db2-backed demo and document its configuration.
- Capture screenshots and record a demo video.
- Fork the official hackathon repository, follow its submission template, and open a pull request.
- Submit that PR link through the official Google Form.

A standalone GitHub repository or Vercel deployment does not replace the required hackathon PR and form submission.
