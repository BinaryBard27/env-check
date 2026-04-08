# env-check 🛡️

**Stop deploying time bombs. Validate your env before it explodes.**

Your .env file is lying to you. `PORT=banana`. `DATABASE_URL=`. `API_KEY=undefined`. Most tools will happily load these into your process without a single complaint. Your app starts anyway—until it hits production and crashes when a deep function finally realizes the configuration was garbage.

**env-check is the Zero-Trust guard for your environment secrets.** It assumes your environment is broken and proves it isn't before a single line of your application logic runs.

---

## 🌊 Why env-check? (The Purple Ocean)

The industry is full of passive "loaders" like `dotenv` and `pythondotenv`. They are glorified file readers that only answer, "Did I find the file?".

**env-check is a pre-deployment config guardrail** that answers, "Is this configuration safe to ship?".

### Zero-Trust Validation
We don't just check for presence; we enforce value correctness, safety, and consistency.

### Explicit, Not Implicit
No magic autoloading that swallows errors. If your config is broken, we fail loudly and clearly.

### Environment-Specific Strictness
Define schemas that know the difference between `.env.dev` and `.env.prod`.

### CI/CD Ready
Pure JSON output and exit codes designed for pipelines—zero promotional noise to break your scripts.

---

## ⚔️ The Comparison: Why the "Standard" Tools Fail

| Feature | env-check | dotenv | envvalid | pythondotenv |
|---------|-----------|--------|----------|--------------|
| **Philosophy** | Gatekeeper | Loader | Validator | Loader |
| **Strictness** | Zero-Trust | Presence Only | High | Presence Only |
| **Logic** | Implicit Loading | No (Secure) | Yes | No (Dangerous) |
| **Env-Specific Logic** | Native | No | Partial | No |
| **Pipeline Safety** | JSON/Stderr | Stdout Noise | Good | Silent Errors |

---

## 🛠️ Quick Start

**"One config. Zero guesswork. Instant validation."**

### Installation

```bash
pip install env-check
```

### Usage

```python
from env_check import EnvGuard

# Define your wall
guard = EnvGuard(schema="env.schema.json")

# envcheck assumes your env is broken—and proves it isn't.
# If it's wrong, it fails LOUDLY here.
guard.protect()
```

---

## 💀 Stop Shipping "undefined"

Passive loaders answer "did it load?" — env-check ensures you survive production.

**Fail at startup or don't run at all. Strong typing or no execution. Not validation. Enforcement.**

⭐ **Star the Repo to join the Zero-Trust movement.** 🛡️