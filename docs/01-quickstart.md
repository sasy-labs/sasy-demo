# Quick Start

Get up and running in 5 minutes.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- An OpenAI API key (for the demo agent)
- A SASY API key (provided to you separately)

## Setup

```bash
# Clone the repo
git clone https://github.com/sasy-labs/sasy-customer-demo.git
cd sasy-customer-demo

# Install dependencies
make setup

# Configure your keys
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY and SASY_API_KEY
```

Your `.env` file should look like:

```bash
OPENAI_API_KEY=sk-...
SASY_API_KEY=demo-key-your-key-here
```

## Run the Demo

```bash
# Upload the policy and run all 9 scenarios
make demo

# Or run interactively (pause between stages)
make demo-step
```

You'll see each scenario play out with the SASY
policy engine authorizing or denying tool calls
in real time.

## What's Happening

1. The demo uploads an airline booking **policy**
   to the SASY cloud service
2. A GPT-powered **agent** handles customer requests
   (cancel reservation, modify flights, etc.)
3. Before each tool call, SASY's **policy engine**
   checks if the action is authorized
4. Denied actions show the reason and a suggestion

## Next Steps

- [Translate your own policy](./02-translate-policy.md)
- [Understand the policy](./03-policy-walkthrough.md)
- [Run individual scenarios](./04-scenarios.md)
