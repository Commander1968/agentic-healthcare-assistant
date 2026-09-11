import json
from pathlib import Path
from typing import Any, Dict


LOG_FILE = Path("logs/pipeline_runs.jsonl")


def log_pipeline_run(
    record: Dict[str, Any],
    log_file: Path = LOG_FILE,
) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open(
        "a",
        encoding="utf-8",
    ) as output_file:
        output_file.write(
            json.dumps(record) + "\n"
        )