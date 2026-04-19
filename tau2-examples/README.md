# Tau2 bench examples

Currently, a toy example of an airline policy (dangerous tool calls require some confirmation from the user, according to simple heuristics) and a basic instrumented equivalent of the `tau2` CLI is included at `tau2_examples/cli.py`.

To run the first test case of the airline domain with this script, run:
```bash
TLS_CERT_PATH=certs/developer.crt TLS_KEY_PATH=certs/developer.key uv run tau2-instrumented run \
--domain airline \
--num-tasks 1 \
--max-steps 10
```
from the repo root.

The certificates are used to authenticate to the RM and observability server; see the Malade example for alternative authentication approaches.

When iterating on the policy, the policy engine must be rebuilt; for this policy, `make docker-up-tau-airline` will do so. In general, the approach is to run:
```
POLICY_FILE=path-to-file docker compose -f docker/docker-compose.yml up -d --build
```
from the repo root. Rerunning the instrumented application will take the new policy into account.
