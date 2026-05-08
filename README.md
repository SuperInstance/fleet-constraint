# Fleet Constraint

**The gatekeeper. Every fleet agent embeds this for safety constraint checking and Keeper communication.**

A fleet of agents is not a fleet just because the agents can reach each other. A fleet is a fleet because the agents share a constraint layer — rules about what's allowed, what's forbidden, and what requires consensus before proceeding.

`fleet-constraint` is that layer. No tile leaves an agent without passing through constraint evaluation. No Keeper command reaches an agent without safety validation. The gatekeeper stands between every agent and every action.

---

## Core Modules

**GuardRuntime** — Load `.guard` files (GD&T-like constraint specifications), compile to FLUX-C bytecode (43-opcode terminating ISA), evaluate constraints at runtime. Guaranteed to terminate. Guaranteed to produce the same result on every machine.

**FleetMathCore** — H¹ emergence detection (sheaf cohomology over the fleet graph), zero-holonomy consensus (cycle detection as agreement), Pythagorean48 trust encoding (48 exact direction vectors).

**KeeperBridge** — [cocapn-glue-core](https://github.com/SuperInstance/cocapn-glue-core) wire protocol for Keeper ↔ Fleet communication. Agents never hold secrets. The Keeper proxies every credential request, issuing time-scoped tokens.

---

## How It Fits

- **[fleet-constraint](https://github.com/SuperInstance/fleet-constraint)** — constraint runtime (this)
- **[fleet-topology](https://github.com/SuperInstance/fleet-topology)** — network topology and routing
- **[fleet-coordinate](https://github.com/SuperInstance/fleet-coordinate)** — spatial coordination on hex lattices
- **[holonomy-consensus](https://github.com/SuperInstance/holonomy-consensus)** — cycle-detection consensus
- **[cocapn-glue-core](https://github.com/SuperInstance/cocapn-glue-core)** — wire protocol across all hardware tiers

---

## License

MIT
