"""ClawBench → Harbor adapter.

The conversion itself lives in the ``clawbench-eval`` package
(``clawbench.eval.harbor_adapter``) so that the adapter and the native runner
can never disagree about instruction text, eval schemas, or the verifier. This
class is the thin ``<Benchmark>Adapter`` wrapper the Harbor adapter guide
expects, with the ``task-template/`` directory kept alongside for reference.
"""

from __future__ import annotations

from pathlib import Path

from clawbench.eval.harbor_adapter import main as convert

TEMPLATE_DIR = Path(__file__).parent / "task-template"


class ClawBenchAdapter:
    def __init__(
        self,
        output_dir: Path,
        *,
        overwrite: bool = False,
        limit: int | None = None,
        task_ids: list[str] | None = None,
        cases_dir: Path | None = None,
        org: str = "clawbench",
        docker_image: str | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.limit = limit
        self.task_ids = task_ids or []
        self.cases_dir = cases_dir
        self.org = org
        self.docker_image = docker_image

    def run(self) -> int:
        argv = ["--output-dir", str(self.output_dir), "--org", self.org]
        if self.overwrite:
            argv.append("--overwrite")
        if self.limit is not None:
            argv += ["--limit", str(self.limit)]
        if self.task_ids:
            argv += ["--task-ids", ",".join(self.task_ids)]
        if self.cases_dir is not None:
            argv += ["--cases-dir", str(self.cases_dir)]
        if self.docker_image:
            argv += ["--docker-image", self.docker_image]
        return convert(argv)
