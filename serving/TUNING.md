# Tuning translate-service for a host

The right process and thread layout depends on the host's CPU count, its memory, and the
traffic it gets. The defaults (`compose.yml`) are conservative. This guide explains each
setting, gives starting points, and shows how to measure on the real host with
`serving/perf-tests/tune.sh`.

## Settings

All of these are environment variables on the `translate-service` container. Set them in
`compose.yml` or with `docker run -e`.

| Variable | Default | What it controls |
|---|---|---|
| `GUNICORN_WORKERS` | 2 | Server processes. **Each one loads every model.** |
| `GUNICORN_THREADS` | 4 | Request threads per process: how many requests one process can hold at the same time. |
| `CTRANSLATE_INTER_THREADS` | 1 | Translations that run in parallel on one model, per process. |
| `CTRANSLATE_INTRA_THREADS` | 4 (6 in `compose.yml`) | CPU threads used by each of those translations. |
| `CTRANSLATE_BEAM_SIZE` | 2 | Search width. 1 is faster and gives slightly worse translations; not benchmarked here. |

How they fit together: a request takes one gunicorn thread, splits its text into sentences,
and sends them as one batch to the model for its language pair. That model runs up to
`INTER` batches at the same time, each using `INTRA` CPU threads. Further requests for the
same pair wait in line. Each process has its own copy of every model and its own queue.

## Rules of thumb

1. **CPU budget.** Keep `WORKERS × INTER × INTRA` about equal to the number of logical CPUs
   the container can use. Going above that makes threads compete for the same cores.
2. **Prefer more `INTER` with a small `INTRA` (2–3).** Interactive requests are short (one or
   a few sentences), and many threads split one short sentence badly. Several translations
   side by side, with a few threads each, use the cores much better. A larger `INTRA` only
   helps with long texts.
3. **`GUNICORN_THREADS` ≥ `INTER` (plus a couple).** With fewer request threads than parallel
   translators, some translators sit idle. Request threads beyond that just wait in line and
   cost almost nothing.
4. **Memory comes from `WORKERS` × models.** About 150 MB per model per process; 3 models
   in one process measured ≈ 450 MB. A higher `INTER` barely adds memory (+30 MB from 2 to 6),
   because the parallel translators share the model weights. With all ~22 models:
   ≈ 3.5 GB for 1 process, ≈ 7 GB for 2. Check the real figure with `/health` (`rss`) or
   `docker stats`.
5. **One process or two:** one process saves memory and gives the highest throughput. Two
   processes keep the service answering while the other one restarts (after a crash or a
   90 s timeout). With one, the service is down while the models reload.
6. **The budget is per model.** Every model has its own pool of `INTER × INTRA` threads. When
   several language pairs are busy at the same moment, they can use more threads than the
   budget in rule 1. Idle pools cost nothing. If mixed traffic is heavy, lean towards a
   smaller `INTER`.
7. **Leave room for translate-batch.** It runs on the same host and translates uploaded files
   with its own CPU threads (see below). Either budget the service for fewer CPUs than the
   host has, or cap the batch container (`cpus:` in `compose.yml`).

## Starting points

Only the 6-core row was measured; the others are extrapolated from the rules above. Confirm
with `tune.sh` on the real host.

| Host (cores / logical CPUs) | WORKERS | THREADS | INTER | INTRA | Notes |
|---|---|---|---|---|---|
| 2 / 4 | 1 | 4 | 2 | 2 | |
| 4 / 8 | 1 | 8 | 4 | 2 | or 2 × (INTER 2 × INTRA 2) to keep a second process |
| 6 / 12 (measured) | 1 | 8 | 4–6 | 3–2 | or 2 × (INTER 3 × INTRA 2) to keep a second process |
| 8 / 16 | 1 | 12 | 8 | 2 | or 2 × (INTER 4 × INTRA 2) |
| 16 / 32 | 2 | 12 | 8 | 2 | two processes cost little memory compared with the RAM such hosts have |

## Reference measurements

Measured in November 2026 with CTranslate2 4.9.1 and beam size 2 on an Intel i9-10900F. The
service was limited to 6 physical cores (12 logical CPUs) and the load generator ran on a
separate core. Each run lasted 15 s with every request on `eng-cat`. "short" is one ~20-word
sentence; "para" is a 63-word, 6-sentence paragraph. Single runs: allow ±10–15%.

| Workers × threads | INTER × INTRA | short req/s (8 / 16 conns) | short median ms (1 / 8 conns) | para req/s (8 / 16) | para median ms (1 conn) | Memory, 3 models |
|---|---|---|---|---|---|---|
| 2 × 4 (default) | 1 × 6 | 12.7 / 12.8 | **79** / 503 | 10.6 / 10.2 | **101** | 830 MB |
| 2 × 4 | 2 × 3 | 14.5 / 14.2 | 95 / 514 | 10.1 / 10.5 | 129 | 860 MB |
| 2 × 4 | 3 × 2 | 21.0 / 20.1 | 109 / 347 | 12.5 / 11.0 | 164 | 849 MB |
| 1 × 8 | 2 × 6 | 14.2 / 14.9 | 95 / 534 | 12.1 / 12.1 | 117 | **449 MB** |
| 1 × 8 | 4 × 3 | 25.0 / 24.1 | 96 / 316 | 12.8 / 12.6 | 133 | 477 MB |
| 1 × 8 | 6 × 2 | **29.9 / 29.7** | 107 / **260** | **14.0 / 14.3** | 165 | 472 MB |

What this shows:
- With the default layout, throughput stays at ~12 req/s however many connections there are.
  6 threads on one short sentence already use all the CPU, inefficiently.
- Moving the same CPU budget to `INTER` gives 2–2.3× the throughput for short requests and
  lower latency under load (p99 at 16 connections: 2565 ms → 643 ms).
- The cost is a slower lone request: about 20–35% when the server is otherwise idle
  (79 → 96–107 ms short, 101 → 133–165 ms paragraph). This is because fewer threads work on
  each request.
- Paragraphs gain less (+35%), because a 6-sentence batch already splits reasonably well
  across `INTRA` threads.

## Measuring on your host

```bash
make docker-build-translate-service
make download-models MODELS=eng-cat          # tune.sh sends eng-cat requests
serving/perf-tests/tune.sh                   # default candidate layouts
serving/perf-tests/tune.sh 2:4:1:6 1:8:4:3   # or your own: WORKERS:THREADS:INTER:INTRA
```

Useful variables (all listed at the top of the script):
- `CPUSET=0-5` limits the service to some CPUs, e.g. to emulate a smaller host or keep CPU free
  for translate-batch. Use `WRK_CPUSET` to put the load generator on other CPUs.
- `MODELS_DIR` points at the full model set, so the memory figure is realistic.
- `DURATION`, `CONCURRENCY` and `PAYLOADS` set run length, connection counts and which
  payloads to send.

Reading the results:
- Look at the concurrency the service really sees. A few simultaneous users means
  4–8 connections; requests rarely arrive one at a time on a busy service.
- Pick the layout with the best req/s there whose 1-connection latency is still acceptable.
- Then check memory with the full model set, and decide whether you need a second process
  for resilience.
- Run the script while the host is otherwise quiet. Other load skews the numbers.

## translate-batch

`model_to_txt` translates a file line by line with `CTRANSLATE_INTER_THREADS` client threads
(defaults: `INTER` 1, `INTRA` 4). Throughput matters more than latency here, so `INTRA` 1 and a
high `INTER` is ideal when the host is otherwise idle. On a host shared with the service,
keep `INTER × INTRA` to the CPUs you can spare. Set the variables on the `translate-batch`
service in `compose.yml`, optionally together with a `cpus:` cap.

## Applying a layout

```yaml
# compose.yml, translate-service
    environment:
        GUNICORN_WORKERS: 1
        GUNICORN_THREADS: 8
        CTRANSLATE_INTER_THREADS: 4
        CTRANSLATE_INTRA_THREADS: 3
        CTRANSLATE_BEAM_SIZE: 2
```

Restart the service (`docker compose up -d`). The new values appear in the startup log line
`device: cpu, inter_threads: …, intra_threads: …`.
