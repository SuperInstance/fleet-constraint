# fleet-constraint

Fleet coordination safety constraint runtime — the binding layer that makes a fleet a fleet.

## What It Does

`fleet-constraint` is a process-level component that fleet agents embed to participate in time-synchronized safety constraint checking and Keeper communication.

Every fleet agent that handles trust-sensitive operations embeds `fleet-constraint` as its **constraint layer**. It is the gatekeeper: no tile leaves the agent without passing through constraint evaluation, and no Keeper command reaches the agent without safety validation.

## Core Modules

- **GuardRuntime** — Load `.guard` files, compile to FLUX-C bytecode, evaluate constraints
- **FleetMathCore** — H1 emergence detection, zero-holonomy consensus, Pythagorean48 trust encoding
- **KeeperBridge** — cocapn-glue-core wire protocol for Keeper ↔ Fleet communication
- **TempoSync** — crystal_sync subprocess wrapper for phase coherence checking
- **SafetyWatcher** — Monitors constraint results and fleet state for safety violations

## Quick Start

```bash
pip install fleet-constraint

# Run the CLI
fleet-constraint --guard safety.guard --keeper-addr keeper.cocapn.local --agent-id murmur-001
```

## Example `.guard` File

```
# safety.guard — fleet constraint definitions
# Format: name:var:op:value:priority[:condition]

h1_guard:h1:<:0.95:10
zhc_guard:zhc:>=:0.85:5:if_phase_SYNC
tempo_guard:tempo:>:0.5:3
drift_guard:drift:<:0.1:2
```

## Embedding in a Domain Agent

```python
from fleet_constraint import GuardRuntime, FleetMathCore, KeeperBridge, SafetyWatcher, TempoSync

runtime = GuardRuntime()
math_core = FleetMathCore()
bridge = KeeperBridge(agent_id="murmur-001")
watcher = SafetyWatcher()

# Load constraints
lines = runtime.load_file("safety.guard")

# Evaluate
results = runtime.evaluate(lines, {"h1": 0.3, "zhc": 0.9, "tempo": 0.8})
for line, satisfied in results:
    print(f"{'✓' if satisfied else '✗'} {line.name}")
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Domain Agents: murmur, spread, whisper-sync     │
├─────────────────────────────────────────────────┤
│  fleet-constraint                               │
│  ├── GuardRuntime    (GUARD DSL → FLUX-C)       │
│  ├── FleetMathCore   (H1, ZHC, Pythagorean48)  │
│  ├── KeeperBridge    (cocapn-glue-core wire)   │
│  ├── TempoSync       (crystal_sync wrapper)    │
│  └── SafetyWatcher   (phase anomaly detection)  │
└─────────────────────────────────────────────────┘
```

## License

MIT
