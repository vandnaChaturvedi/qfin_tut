#!/usr/bin/env python3
"""
Auto-fix all qiskit-finance tutorial notebooks for the qfin environment.

Fixes applied:
  1. Copy tutorial_magics.py to qfin site-packages (permanent, all 12 notebooks)
     — tutorial_magics cells in notebooks are LEFT UNTOUCHED
  2. Notebook 00: StatevectorSampler already active — verify only
  3. Notebooks 01, 02: AerSampler V1 → V2  +  TwoLocal class → n_local function
  4. Notebook 02: cplex graceful fallback message
"""

import json
import os
import shutil
import glob

TUTORIALS_DIR = os.path.dirname(os.path.abspath(__file__))
QFIN_SITEPACKAGES = os.path.expanduser(
    "~/anaconda3/envs/qfin/lib/python3.12/site-packages"
)


# ── Fix 1: copy tutorial_magics to site-packages ──────────────────────────────
def fix_tutorial_magics_sitepackages():
    src = os.path.join(TUTORIALS_DIR, "tutorial_magics.py")
    dst = os.path.join(QFIN_SITEPACKAGES, "tutorial_magics.py")
    if os.path.exists(dst):
        print(f"  [SKIP] tutorial_magics.py already in site-packages")
        return
    try:
        shutil.copy2(src, dst)
        print(f"  [OK]   Copied tutorial_magics.py → {dst}")
    except Exception as e:
        print(f"  [WARN] Could not copy to site-packages: {e}")


# ── Fix 2: Aer Sampler → StatevectorSampler ───────────────────────────────────
# qiskit_aer.primitives.Sampler is V1 → fails with V2-style PUBs used by
# SamplingVQE / QAOA in qiskit_algorithms 0.4.0.
# qiskit_aer.primitives.SamplerV2 is V2 but uses the Aer C++ backend which
# cannot handle high-level gate instructions (QAOA, QPE) → AerError.
# Fix: qiskit.primitives.StatevectorSampler is V2 AND handles high-level gates.
def fix_sampler_v1_to_v2(nb, nb_name):
    changed = False
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src = cell.get("source", [])
        src_str = "".join(src)

        # Already fully patched
        if "StatevectorSampler as Sampler" in src_str:
            print(f"  [SKIP] {nb_name} cell[{i}] — StatevectorSampler already present")
            continue

        # Original V1 import
        if "from qiskit_aer.primitives import Sampler" in src_str:
            lines = src if isinstance(src, list) else src_str.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if ("from qiskit_aer.primitives import Sampler" in line
                        and not stripped.startswith("#")):
                    new_lines.append("# " + line if not line.startswith("# ") else line)
                elif ("from qiskit_aer.primitives import SamplerV2" in line
                        and not stripped.startswith("#")):
                    new_lines.append("# " + line if not line.startswith("# ") else line)
                else:
                    new_lines.append(line)
            new_lines.append(
                "from qiskit.primitives import StatevectorSampler as Sampler"
                "  # V2 + handles QAOA/QPE high-level gates\n"
            )
            cell["source"] = new_lines
            print(f"  [OK]   {nb_name} cell[{i}] — Aer Sampler → StatevectorSampler (aliased as Sampler)")
            changed = True
            continue

        # Previously patched to SamplerV2 (wrong) — upgrade to StatevectorSampler
        if "from qiskit_aer.primitives import SamplerV2 as Sampler" in src_str:
            lines = src if isinstance(src, list) else src_str.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                if ("from qiskit_aer.primitives import SamplerV2 as Sampler" in line
                        and not line.strip().startswith("#")):
                    new_lines.append("# " + line if not line.startswith("# ") else line)
                    new_lines.append(
                        "from qiskit.primitives import StatevectorSampler as Sampler"
                        "  # V2 + handles QAOA/QPE high-level gates\n"
                    )
                else:
                    new_lines.append(line)
            cell["source"] = new_lines
            print(f"  [OK]   {nb_name} cell[{i}] — SamplerV2 → StatevectorSampler (handles QAOA/QPE)")
            changed = True

    return changed


# ── Fix 3: TwoLocal class — keep as-is (DO NOT alias to n_local) ──────────────
# n_local() returns a plain QuantumCircuit whose num_qubits cannot be set.
# SamplingVQE._check_operator_ansatz() tries to resize the ansatz via
# ansatz.num_qubits = operator.num_qubits — this requires a BlueprintCircuit.
# TwoLocal class IS a BlueprintCircuit with a settable num_qubits, so we keep it.
# The DeprecationWarning is acceptable; TwoLocal class is removed in Qiskit 3.0 only.
def fix_twolocal_deprecation(nb, nb_name):
    # Revert any prior n_local-as-TwoLocal alias back to the TwoLocal class.
    changed = False
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src_str = "".join(cell.get("source", []))
        if ("# from qiskit.circuit.library import TwoLocal\n"
                "from qiskit.circuit.library import n_local as TwoLocal") not in src_str:
            continue
        new_src = src_str.replace(
            "# from qiskit.circuit.library import TwoLocal\n"
            "from qiskit.circuit.library import n_local as TwoLocal"
            "  # TwoLocal class deprecated in Qiskit 2.1",
            "from qiskit.circuit.library import TwoLocal"
            "  # BlueprintCircuit: SamplingVQE needs settable num_qubits",
        )
        if new_src != src_str:
            cell["source"] = new_src.splitlines(keepends=True)
            print(f"  [OK]   {nb_name} cell[{i}] — reverted n_local alias → TwoLocal class (BlueprintCircuit)")
            changed = True
    return changed


# ── Fix 4: notebook 02 — cplex graceful fallback ─────────────────────────────
def fix_nb02_cplex(nb, nb_name):
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src_str = "".join(cell.get("source", []))

        if "import cplex" not in src_str:
            continue
        if "pip install cplex" in src_str:
            print(f"  [SKIP] {nb_name} cell[{i}] — cplex fallback already present")
            continue

        lines = cell["source"] if isinstance(cell["source"], list) \
                else src_str.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.strip() == "except Exception as ex:":
                new_lines.append(
                    "    print('[INFO] cplex not installed — skipping classical comparison. "
                    "Install: pip install cplex')\n"
                )
        cell["source"] = new_lines
        print(f"  [OK]   {nb_name} cell[{i}] — improved cplex fallback message")
        return True
    return False


# ── Fix 5: print_result — handle SamplerV2 plain-dict eigenstate ─────────────
# SamplerV2 stores eigenstate as a plain dict (int keys → quasi-probs).
# The original code's else-branch calls .to_dict() which doesn't exist on dict.
OLD_PRINT_RESULT = (
    "    probabilities = (\n"
    "        eigenstate.binary_probabilities()\n"
    "        if isinstance(eigenstate, QuasiDistribution)\n"
    "        else {k: np.abs(v) ** 2 for k, v in eigenstate.to_dict().items()}\n"
    "    )"
)
NEW_PRINT_RESULT = (
    "    if isinstance(eigenstate, QuasiDistribution):\n"
    "        probabilities = eigenstate.binary_probabilities()\n"
    "    elif isinstance(eigenstate, dict) and isinstance(next(iter(eigenstate), None), int):\n"
    "        # SamplerV2 returns plain dict with int keys; convert to binary strings\n"
    "        probabilities = {format(k, f'0{len(selection)}b'): abs(v) for k, v in eigenstate.items()}\n"
    "    elif isinstance(eigenstate, dict):\n"
    "        probabilities = eigenstate\n"
    "    else:\n"
    "        probabilities = {k: np.abs(v) ** 2 for k, v in eigenstate.to_dict().items()}"
)


def fix_print_result(nb, nb_name):
    changed = False
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src_str = "".join(cell.get("source", []))
        if OLD_PRINT_RESULT not in src_str:
            if "SamplerV2 returns plain dict" in src_str:
                print(f"  [SKIP] {nb_name} cell[{i}] — print_result already patched")
            continue

        new_src = src_str.replace(OLD_PRINT_RESULT, NEW_PRINT_RESULT)
        cell["source"] = new_src.splitlines(keepends=True)
        print(f"  [OK]   {nb_name} cell[{i}] — print_result: SamplerV2 plain-dict eigenstate handled")
        changed = True
    return changed


# ── Fix 6: notebooks 03-10 — Aer V1 Sampler import → StatevectorSampler ──────
# qiskit_aer.primitives.Sampler is V1; qiskit_algorithms 0.4.0 passes V2 PUBs.
# Also converts run_options={"shots": N, "seed": S} → default_shots=N, seed=S.
def fix_aer_sampler_import_and_run_options(nb, nb_name):
    changed = False
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src_str = "".join(cell.get("source", []))
        cell_changed = False

        # Fix import
        if ("from qiskit_aer.primitives import Sampler" in src_str
                and "StatevectorSampler" not in src_str):
            lines = cell["source"] if isinstance(cell["source"], list) \
                    else src_str.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                if ("from qiskit_aer.primitives import Sampler" in line
                        and not line.strip().startswith("#")):
                    commented = ("# " + line if not line.startswith("# ") else line)
                    if not commented.endswith("\n"):
                        commented += "\n"
                    new_lines.append(commented)
                    new_lines.append(
                        "from qiskit.primitives import StatevectorSampler as Sampler"
                        "  # V2: handles IAE/AE circuits\n"
                    )
                else:
                    new_lines.append(line)
            cell["source"] = new_lines
            src_str = "".join(new_lines)
            print(f"  [OK]   {nb_name} cell[{i}] — Aer Sampler → StatevectorSampler")
            cell_changed = True

        # Fix instantiation: Sampler(run_options={"shots": N, "seed": S})
        #                  → Sampler(default_shots=N, seed=S)
        import re
        pattern = r'Sampler\(run_options=\{"shots":\s*(\d+),\s*"seed":\s*(\d+)\}\)'
        if re.search(pattern, src_str):
            def repl(m):
                return f'Sampler(default_shots={m.group(1)}, seed={m.group(2)})'
            new_src = re.sub(pattern, repl, src_str)
            if new_src != src_str:
                cell["source"] = new_src.splitlines(keepends=True)
                src_str = new_src
                print(f"  [OK]   {nb_name} cell[{i}] — Sampler(run_options=...) → Sampler(default_shots=..., seed=...)")
                cell_changed = True

        changed |= cell_changed
    return changed


# ── Fix 7: notebooks 06/07/09 — bare sampler.run(circuit) → sampler.run([circuit])
#           and V1 quasi_dists result → V2 BitArray result ───────────────────────
# V2 StatevectorSampler.run() requires a list of PUBs, not a bare circuit.
# V1 result: job.result().quasi_dists[0].binary_probabilities()
# V2 result: {k: v/sum(...) for k,v in job.result()[0].data.meas.get_counts().items()}
def fix_sampler_run_and_quasi_dists(nb, nb_name):
    import re
    changed = False
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src_str = "".join(cell.get("source", []))
        new_src = src_str

        # Fix bare sampler.run(var) → sampler.run([var])
        # Match sampler.run( followed by anything that is NOT already '[' or 'Sampler'
        new_src = re.sub(
            r'\bsampler\.run\(([^[\(][^\)]*)\)',
            lambda m: f'sampler.run([{m.group(1)}])',
            new_src,
        )

        # Fix V1 quasi_dists result → V2 BitArray result
        new_src = new_src.replace(
            "job.result().quasi_dists[0].binary_probabilities()",
            "{k: v/sum(job.result()[0].data.meas.get_counts().values())"
            " for k, v in job.result()[0].data.meas.get_counts().items()}",
        )

        if new_src != src_str:
            cell["source"] = new_src.splitlines(keepends=True)
            print(f"  [OK]   {nb_name} cell[{i}] — sampler.run/quasi_dists V2 fix")
            changed = True
    return changed


# ── Fix 8: remove old auto-install cell from nb 00 (cleanup) ─────────────────
def remove_auto_install_cell(nb, nb_name):
    if not nb["cells"]:
        return False
    first = nb["cells"][0]
    if first.get("cell_type") == "code":
        src = "".join(first.get("source", []))
        if "subprocess.check_call" in src and "qiskit" in src:
            nb["cells"].pop(0)
            print(f"  [OK]   {nb_name} cell[0] — removed old auto-install cell")
            return True
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  qiskit-finance notebook auto-fixer")
    print("=" * 65)

    print("\n[1] Copying tutorial_magics.py to qfin site-packages...")
    fix_tutorial_magics_sitepackages()

    notebooks = sorted(glob.glob(os.path.join(TUTORIALS_DIR, "*.ipynb")))
    print(f"\n[2] Patching {len(notebooks)} notebooks in:\n    {TUTORIALS_DIR}\n")

    total_changes = 0

    # These notebooks are confirmed correct — never touch them
    FROZEN = {
        "00_amplitude_estimation.ipynb",
        "01_portfolio_optimization.ipynb",
        "02_portfolio_diversification.ipynb",
        "03_european_call_option_pricing.ipynb",
        "04_european_put_option_pricing.ipynb",
        "05_bull_spread_pricing.ipynb",
        "06_basket_option_pricing.ipynb",
        "07_asian_barrier_spread_pricing.ipynb",
        "08_fixed_income_pricing.ipynb",
        "09_credit_risk_analysis.ipynb",
        "10_qgan_option_pricing.ipynb",
        "11_time_series.ipynb",
    }

    for nb_path in notebooks:
        nb_name = os.path.basename(nb_path)

        if nb_name in FROZEN:
            print(f"  → Skipped (frozen): {nb_name}")
            continue

        with open(nb_path, encoding="utf-8") as f:
            nb = json.load(f)

        changed = False

        # tutorial_magics cells LEFT UNTOUCHED in all notebooks

        # Notebook 00: cleanup only (now frozen, block above handles it)
        if nb_name == "00_amplitude_estimation.ipynb":
            changed |= remove_auto_install_cell(nb, nb_name)

        # Notebooks 01, 02: Sampler V1→V2 + TwoLocal→n_local + print_result patch
        if nb_name in ("01_portfolio_optimization.ipynb",
                       "02_portfolio_diversification.ipynb"):
            changed |= fix_sampler_v1_to_v2(nb, nb_name)
            changed |= fix_twolocal_deprecation(nb, nb_name)
            changed |= fix_print_result(nb, nb_name)

        # Notebook 02 only: cplex fallback
        if nb_name == "02_portfolio_diversification.ipynb":
            changed |= fix_nb02_cplex(nb, nb_name)

        # Notebooks 03-10: Aer V1 Sampler → StatevectorSampler + run_options fix
        if nb_name not in ("00_amplitude_estimation.ipynb",
                           "01_portfolio_optimization.ipynb",
                           "02_portfolio_diversification.ipynb"):
            changed |= fix_aer_sampler_import_and_run_options(nb, nb_name)

        # Notebooks 06/07/09: bare sampler.run(circuit) + quasi_dists V1 result
        if nb_name in ("06_basket_option_pricing.ipynb",
                       "07_asian_barrier_spread_pricing.ipynb",
                       "09_credit_risk_analysis.ipynb"):
            changed |= fix_sampler_run_and_quasi_dists(nb, nb_name)

        if changed:
            with open(nb_path, "w", encoding="utf-8") as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            total_changes += 1
            print(f"  → Saved: {nb_name}")
        else:
            print(f"  → No changes: {nb_name}")

    print(f"\n{'=' * 65}")
    print(f"  Done. {total_changes}/{len(notebooks)} notebooks updated.")
    print(f"  Restart your Jupyter kernel and re-run all cells.")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
