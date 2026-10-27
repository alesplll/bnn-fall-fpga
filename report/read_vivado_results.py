"""Validate one Vivado 2022.2 PR2/PR3 run and extract report figures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CASES = (
    "pr2_classifier",
    "baseline_20",
    "pipeline_20",
    "baseline_10",
    "pipeline_10",
    "pr3_prototype_20",
    "pr3_pipeline_20",
)
ROUTED = set(CASES) - {"pr2_classifier"}
SIMS = (
    ("sim_pr2_behavioral.log", "PASS: 2331 vectors"),
    ("sim_pipeline_behavioral.log", "PASS: pipelined classifier, 2331 vectors"),
    ("sim_pr3_behavioral.log", "PASS: FPGA prototype self-test"),
    ("sim_pr3_pipeline_behavioral.log", "PASS: pipelined prototype"),
    ("sim_benchmark_baseline_behavioral.log", "PASS: benchmark baseline, 2331 vectors"),
    ("sim_benchmark_pipeline_behavioral.log", "PASS: benchmark pipelined, 2331 vectors"),
    ("sim_benchmark_baseline_post-synthesis.log", "PASS: benchmark baseline, 2331 vectors"),
    ("sim_benchmark_pipeline_post-synthesis.log", "PASS: benchmark pipelined, 2331 vectors"),
)
RESOURCE_NAMES = ("Slice LUTs", "Slice Registers", "Slice", "Bonded IOB", "BUFGCTRL", "Block RAM Tile", "DSPs")


def get(text: str, pattern: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing {label}")
    return match.group(1)


def resources(path: Path) -> dict[str, dict[str, float]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result = {}
    for name in RESOURCE_NAMES:
        pattern = rf"^\|\s*{re.escape(name)}\s*\|\s*(\d+)\s*\|[^\n]*\|\s*([\d.]+)\s*\|$"
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            result[name] = {"used": int(match.group(1)), "percent": float(match.group(2))}
        elif name in ("Block RAM Tile", "DSPs"):
            result[name] = {"used": 0, "percent": 0.0}
        else:
            raise ValueError(f"Missing resource {name} in {path}")
    return result


def parse(root: Path) -> dict:
    summary = {"source": str(root), "cases": {}, "simulations": {}}
    for filename, marker in SIMS:
        path = root / "simulations" / filename
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker not in text or "FAIL:" in text:
            raise ValueError(f"Simulation did not pass: {path}")
        summary["simulations"][filename] = "PASS"
    for name in CASES:
        folder = root / name
        result = dict(line.split("=", 1) for line in (folder / "result.txt").read_text().splitlines() if "=" in line)
        if "Complete" not in result.get("synthesis_status", ""):
            raise ValueError(f"Synthesis not complete: {name}")
        item = {"top": result["top"], "synthesis": resources(folder / "utilization_synth.rpt")}
        log = (folder / "synth.log").read_text(encoding="utf-8", errors="replace")
        for mem in ("weights_layerA_W.mem", "weights_layerA_b.mem", "weights_layerB_W.mem", "weights_layerB_b.mem"):
            if f"data file '{mem}' is read successfully" not in log:
                raise ValueError(f"Memory {mem} not confirmed in {name}")
        item["synthesis_warnings"] = re.findall(r"^WARNING: \[([^]]+)\] ([^\n]+)", log, re.MULTILINE)
        if name in ROUTED:
            if "Complete" not in result.get("implementation_status", ""):
                raise ValueError(f"Implementation not complete: {name}")
            item["routed"] = resources(folder / "utilization_routed.rpt")
            item["period_ns"] = float(result["actual_period_ns"])
            item["wns_ns"] = float(result["worst_setup_slack_ns"])
            route = (folder / "route_status.rpt").read_text(encoding="utf-8", errors="replace")
            item["routable_nets"] = int(get(route, r"# of routable nets\.+\s*:\s*(\d+)", "routable nets"))
            item["routed_nets"] = int(get(route, r"# of fully routed nets\.+\s*:\s*(\d+)", "routed nets"))
            item["routing_errors"] = int(get(route, r"# of nets with routing errors\.+\s*:\s*(\d+)", "route errors"))
            if item["routed_nets"] != item["routable_nets"] or item["routing_errors"]:
                raise ValueError(f"Incomplete routing: {name}")
            timing = (folder / "timing_routed.rpt").read_text(encoding="utf-8", errors="replace")
            item["input_ports_without_delay"] = int(get(timing, r"There are (\d+) input ports with no input delay specified", "input delay"))
            item["output_ports_without_delay"] = int(get(timing, r"There are (\d+) ports with no output delay specified", "output delay"))
            for label in ("no_clock", "unconstrained_internal_endpoints", "latch_loops"):
                count = int(get(timing, rf"checking {label} \((\d+)\)", label))
                if count:
                    raise ValueError(f"{name} has {count} {label} violations")
            drc = (folder / "drc_routed.rpt").read_text(encoding="utf-8", errors="replace")
            item["drc_rules"] = re.findall(r"^\|\s*([A-Z0-9-]+)\s*\|\s*(?:Critical Warning|Warning|Error)", drc, re.MULTILINE)
        summary["cases"][name] = item
    return summary


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python report/read_vivado_results.py vivado_pr23/results")
    print(json.dumps(parse(Path(sys.argv[1])), ensure_ascii=False, indent=2))
