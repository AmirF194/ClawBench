# ClawBench × Harbor

This directory packages ClawBench in the [Harbor](https://github.com/harbor-framework/harbor) task format so anyone who already evaluates agents with `harbor run` can score them on ClawBench without learning our CLI. It has three parts, each aimed at a different distribution channel:

| Part | Channel | Who uses it |
| --- | --- | --- |
| [`../registry.json`](../registry.json) + [`datasets/clawbench-v2/`](datasets/clawbench-v2/) | **Git registry** — `harbor run --repo TIGER-AI-Lab/ClawBench -d clawbench-v2` | Anyone, today, no publishing step |
| [`dataset.toml`](dataset.toml) | **Harbor Hub** — `harbor publish` → `harbor run -d tiger-ai-lab/clawbench-v2` | Maintainers publish once; users pull by name |
| [`adapter/`](adapter/) | **Upstream adapter** — PR to `harbor-framework/harbor/adapters/clawbench` + `laude-institute/harbor-datasets` | Gets ClawBench into the official adapter list / registry and eligible for Harbor-Index |

The task content is *generated* from [`test-cases/v2/`](../test-cases/v2/) by [`clawbench-harbor-adapt`](../docs/harbor.md); nothing here is hand-edited. `scripts/harbor/regenerate.sh` rebuilds all of it and CI fails if the committed copy is stale.

## Run ClawBench through Harbor (git registry)

```bash
uv tool install harbor            # Harbor ≥ 0.22

harbor run --repo TIGER-AI-Lab/ClawBench -d clawbench-v2 \
  -a hermes -m deepseek/deepseek-v4-flash \
  --env-file .env \
  --ve CLAWBENCH_JUDGE_BASE_URL=... --ve CLAWBENCH_JUDGE_API_KEY=... \
  --ve CLAWBENCH_JUDGE_MODEL=deepseek-v4-pro --ve CLAWBENCH_JUDGE_API_TYPE=openai-completions \
  -n 8
```

- Pin a release with `--repo TIGER-AI-Lab/ClawBench@v0.9.2`.
- `-i 'v2-9*'` / `-x '...'` include or exclude tasks by glob.
- Judge wiring, concurrency, and troubleshooting: [`docs/harbor.md`](../docs/harbor.md).

**Runtime image.** Committed tasks are in *prebuilt mode*: `task.toml` points `[environment].docker_image` at `clawbench/clawbench-harbor-runtime (Docker Hub):<clawbench version>` instead of shipping a 280 KB `environment/` build context per task (129 × 280 KB ≈ 35 MB otherwise). The image is built from [`src/clawbench/runtime/harbor/Dockerfile`](../src/clawbench/runtime/harbor/Dockerfile) by `scripts/harbor/build-runtime-image.sh` and published by the `publish-harbor-image` workflow on release tags / manual dispatch (repo secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`). If you want tasks that build locally instead, generate them yourself:

```bash
uv run clawbench-harbor-adapt --output-dir ./harbor-datasets/clawbench-v2 --overwrite
harbor run -p ./harbor-datasets/clawbench-v2 -a hermes -m deepseek/deepseek-v4-flash ...
```

## Publish to the Harbor Hub (maintainers)

The Hub is the registry behind `harbor run -d <org>/<dataset>` and the leaderboards on hub.harborframework.com. One-time setup, then one command per release:

```bash
harbor auth login                                   # GitHub OAuth; creates org = your GitHub login
harbor auth org create tiger-ai-lab                 # or ask an existing member to add you

# Task names in dataset.toml are <org>/<task>; the org must be one you own on the Hub.
scripts/harbor/regenerate.sh                        # refresh datasets/, registry.json, dataset.toml

harbor publish harbor/dataset.toml harbor/dataset-v1.toml --public -t v0.9.2
harbor run -d tiger-ai-lab/clawbench-v2@v2 -a hermes -m ...   # anyone, anywhere
```

`harbor publish` uploads the task directories referenced by the manifest, so the Hub copy does not depend on this git repo. Visibility defaults to private; `--public` applies to new packages only (`harbor dataset visibility` for existing ones).

## Upstream to harbor-framework (adapter + registry + Harbor-Index)

Harbor's official adapters live in `harbor-framework/harbor/adapters/<name>/` and their generated datasets in `laude-institute/harbor-datasets/datasets/<name>/`; `registry.json` in the harbor repo ties the two together. The process (from [harborframework.com/docs/datasets/adapters](https://www.harborframework.com/docs/datasets/adapters)):

1. `adapter/` here is already in the `harbor adapter init` layout (README template sections, `adapter_metadata.json`, `parity_experiment.json`, `run_clawbench.yaml`, `src/clawbench_adapter/{adapter,main}.py`, `task-template/`). Copy it to a harbor fork as `adapters/clawbench/`, branch `clawbench-adapter`.
2. `harbor adapter review -p adapters/clawbench --skip-ai` — structural validation (required files, JSON schemas, README sections).
3. Oracle check: ClawBench has no scripted browser oracle (live sites), so document that `solution/solve.sh` is a no-op and that verifier correctness is demonstrated by the parity run instead.
4. Open `[WIP] Adapter: clawbench` on harbor-framework/harbor; coordinate parity on Discord `#adapters-announcements` (Lin Shi, adapters lead). 2077AI-sponsored parity API keys: `adapters/parity_api_instructions.md`.
5. **Parity experiment** — same agent on both sides: `clawbench-batch --harness hermes` (original) vs `harbor run -a hermes` (adapter), ≥3 runs each, report mean ± sample SEM for Intercepted and Reward-lenient; match when the run ranges overlap. Fill `parity_experiment.json`, upload artifacts to `harborframework/parity-experiments` on Hugging Face.
6. PR generated tasks to `laude-institute/harbor-datasets` under `datasets/clawbench/` with a `dataset.toml` + README; add the `clawbench` entry to harbor's `registry.json`.
7. Retitle `[Ready for Review] Adapter: clawbench`, request review from @Slimshilin.

Harbor-Index (harbor-index.org) is curated *from* registered adapters (tasks with ≤33 % frontier solve rate, broken-task audit, human review) — there is no direct submission; step 6 is the prerequisite.

## Layout

```
harbor/
├── README.md              this file
├── dataset.toml           Hub manifest: tiger-ai-lab/clawbench-v2
├── dataset-v1.toml        Hub manifest: tiger-ai-lab/clawbench-v1
├── job-config.yaml        harbor run -c harbor/job-config.yaml (local docker, hermes)
├── adapter/               harbor-framework/harbor adapters/clawbench package
└── datasets/
    ├── clawbench-v2/      129 generated prebuilt-mode tasks (leaderboard corpus)
    └── clawbench-v1/      152 generated prebuilt-mode tasks (V1 corpus)
../registry.json           git registry consumed by --repo
```
