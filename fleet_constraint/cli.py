"""fleet-constraint CLI — main entry point for the constraint runtime."""

import argparse
import sys
import time
from pathlib import Path
from fleet_constraint.guard_runtime import GuardRuntime, ConstraintStatus, ConstraintResult
from fleet_constraint.fleet_math_core import FleetMathCore
from fleet_constraint.keeper_bridge import KeeperBridge
from fleet_constraint.tempo_sync import TempoSync
from fleet_constraint.safety_watcher import SafetyWatcher


def main():
    parser = argparse.ArgumentParser(
        description="fleet-constraint — Fleet coordination safety constraint runtime"
    )
    parser.add_argument(
        "--guard",
        type=str,
        help="Path to .guard constraint file",
    )
    parser.add_argument(
        "--keeper-addr",
        type=str,
        default="localhost",
        help="Keeper address (hostname or IP)",
    )
    parser.add_argument(
        "--keeper-port",
        type=int,
        default=8901,
        help="Keeper port",
    )
    parser.add_argument(
        "--tick-interval",
        type=float,
        default=1.0,
        help="Tick interval in seconds",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="fleet-agent-001",
        help="Agent identifier",
    )
    parser.add_argument(
        "--halt-on-violation",
        action="store_true",
        help="Halt the loop immediately on constraint violation",
    )

    args = parser.parse_args()

    runtime = GuardRuntime()
    math_core = FleetMathCore()
    tempo_sync = TempoSync()
    safety_watcher = SafetyWatcher()
    bridge = KeeperBridge(agent_id=args.agent_id)

    # Load guard file if provided
    guard_lines = []
    if args.guard:
        path = Path(args.guard)
        if not path.exists():
            print(f"ERROR: Guard file not found: {args.guard}", file=sys.stderr)
            sys.exit(1)
        try:
            guard_lines = runtime.load_file(str(path))
            print(f"Loaded {len(guard_lines)} guard constraints from {args.guard}")
        except Exception as e:
            print(f"ERROR loading guard file: {e}", file=sys.stderr)
            sys.exit(1)

    # Try to connect to Keeper
    keeper_connected = bridge.connect(args.keeper_addr, args.keeper_port)
    if keeper_connected:
        print(f"Connected to Keeper at {args.keeper_addr}:{args.keeper_port}")
    else:
        print(f"WARNING: Could not connect to Keeper at {args.keeper_addr}:{args.keeper_port} — running in dry-run mode")

    tick = 0
    try:
        while True:
            # Build evaluation context
            context = {
                "tick": float(tick),
                "tempo": 1.0,  # default
            }

            # Read phase offsets from crystal_sync
            offsets = tempo_sync.read_phase_offsets()
            drift = tempo_sync.check_coherence(offsets)
            context["drift"] = drift

            # Evaluate guard constraints
            if guard_lines:
                results = runtime.evaluate(guard_lines, context)
                for line, satisfied in results:
                    status_str = "✓" if satisfied else "✗"
                    print(f"[tick={tick}] {status_str} {line.name}: {line.var} {line.op} {line.value}")

                # Build constraint results for safety watcher
                constraint_results = []
                for line, satisfied in results:
                    status = ConstraintStatus.SATISFIED if satisfied else ConstraintStatus.VIOLATED
                    cr = ConstraintResult(name=line.name, status=status, tick=tick)
                    constraint_results.append(cr)

                # Safety check
                fleet_state = {
                    "h1": 0.0,
                    "zhc": 1.0,
                    "phase": "GUARD",
                    "drift": drift,
                }
                alert = safety_watcher.monitor(constraint_results, fleet_state)
                if alert:
                    print(f"[tick={tick}] SAFETY ALERT: {alert}")
                    if args.halt_on_violation:
                        print("Halting due to constraint violation.")
                        break
            else:
                print(f"[tick={tick}] No guard constraints loaded — idle tick")

            tick += 1
            time.sleep(args.tick_interval)

    except KeyboardInterrupt:
        print("\nShutting down fleet-constraint.")
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
