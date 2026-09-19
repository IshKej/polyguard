# Deploying PolyGuard to a public URL (free)

Goal: a live `https://polyguard.streamlit.app` link you can put in the Congressional App Challenge demo video and submission. Free, no credit card.

You do the two account steps (they must be under your name); everything else is already set up in this repo.

## 1. Put the code on GitHub

1. Make a free account at https://github.com if you don't have one.
2. Create a new **public** repository named `polyguard`.
3. Upload every file in this folder **except** `.streamlit/secrets.toml` (that holds the key — `.gitignore` already blocks it). The easy way: GitHub repo page → **Add file → Upload files** → drag in `app.py`, `engine.py`, `providers.py`, `defenses.py`, `attack_bank.json`, `generate_attack_bank.py`, `languages_catalog.py`, `expand_languages.py`, `validate_bank.py`, `test_engine.py`, `verify_all.py`, `selection_bias_demo.py`, `requirements.txt`, `README.md`, `DEPLOY.md`, `AUDIT.md`, `PREREGISTRATION.md`, and the `.streamlit/config.toml` file. Commit.

> `attack_bank.json` must be in the repo — Streamlit Cloud loads it and does not run the generators. It is already in your local folder (produced by `generate_attack_bank.py`, then expanded by `expand_languages.py`). If you ever regenerate it, re-upload it.

> Double-check: `secrets.toml` must NOT be in the repo. Only `config.toml` and `secrets.toml.example` belong there.

## 2. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in **with GitHub**.
2. **Create app** → pick your `polyguard` repo, branch `main`, main file `app.py`.
3. Before deploying, open **Advanced settings → Secrets** and paste:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   (your real Anthropic key — this stays private on Streamlit's side, never in GitHub).

   Optional, only if you want to scan other vendors' models too. Any you leave
   out simply show as unavailable in the model picker:
   ```
   OPENAI_API_KEY = "sk-..."
   GOOGLE_API_KEY = "..."
   GROQ_API_KEY   = "gsk_..."
   ```
4. **Deploy.** First build takes a couple of minutes.

You now have a public URL. Anyone who opens it runs live scans against the demo bots.

## 3. If you'd rather not expose your API key publicly

A public app means anyone visiting spends your API credits. Two safe options:

- **Keep it in MOCK mode for the public link** and run the *live* scan only on your laptop during the demo video. The app already labels mock vs live clearly.
- **Add a passcode gate** (ask me — it's ~15 lines) so only you can trigger live scans, and everyone else sees the interface.

On a student budget, recording the live scan in the video and leaving the public link in mock mode is the sensible move. Judges watch the video; the link is a bonus.

## 3b. Before trusting a new provider, smoke-test it

The Anthropic path is covered by the test suite. The OpenAI, Google and
OpenAI-compatible adapters are written to each vendor's documented request shape
but have never run against a live key, so prove them before you believe a number
that comes out of them:

```bash
python providers.py            # which models are ready, and what each one still needs
python providers.py --smoke    # one harmless call per configured provider
```

Every configured model must print PASS. A FAIL means that adapter's request shape
needs fixing, not that the model is vulnerable.

## 4. Cost sanity check

One live scan fires **5 categories × 3 phrasings = 15 short calls to the victim model per language**, plus a judge call only when a reply actually contains the canary. So a 12-language demo scan is ~180 calls, and a full 87-language scan is ~1,305 calls. On the default victim (Claude Haiku) that lands in the low tens of cents even for the full scan, and the phrasings slider drops it to a third if you set it to 1.

Each scan also fires **6 benign capability controls per language** (522 calls on a full 87-language scan) to check the bot can follow ordinary instructions in that language at all. Without them a quiet language cannot be told apart from a broken one.

Scanning several vendors multiplies all of that by the number of models, and each vendor bills separately. Start with one model and one tier of languages before running the full cross-model sweep.

The thing that could actually add up is a public link with no gate, where every visitor spends your credits. That is why option 3 exists.
