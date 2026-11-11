"""Execute the direct notebook and optionally collect paid runs."""

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from matplotlib_inline.backend_inline import configure_inline_support


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Collect the three runs using the configured paid model API.",
    )
    args = parser.parse_args()
    path = Path(__file__).with_name(
        "ticket_classification_evaluation_direct.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    os.chdir(path.parents[3])
    shell = InteractiveShell.instance()
    matplotlib.use("module://matplotlib_inline.backend_inline")
    configure_inline_support(shell, "inline")
    count = 0
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        count += 1
        source = "".join(cell["source"])
        if args.collect and "RUN_ANALYSIS = False" in source:
            source = source.replace(
                "RUN_ANALYSIS = False", "RUN_ANALYSIS = True"
            )
        print(f"Executing cell {index}...", flush=True)
        with capture_output() as captured:
            result = shell.run_cell(source, store_history=False)
        outputs = []
        for name, content in [
            ("stdout", captured.stdout),
            ("stderr", captured.stderr),
        ]:
            if content:
                outputs.append(
                    {"output_type": "stream", "name": name, "text": content}
                )
        for output in captured.outputs:
            outputs.append(
                {
                    "output_type": "display_data",
                    "data": output.data,
                    "metadata": output.metadata,
                }
            )
        cell["execution_count"] = count
        cell["outputs"] = outputs
        path.write_text(
            json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if result.error_before_exec or result.error_in_exec:
            print(captured.stdout, captured.stderr, file=sys.stderr)
            raise SystemExit(1)
    print(f"Saved executed notebook: {path}", flush=True)


if __name__ == "__main__":
    main()
