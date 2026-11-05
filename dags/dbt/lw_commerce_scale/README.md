# lw_commerce_scale

Synthetic fan-out project for **parse/compile** benchmarks (~750 models: 250 per layer).

Regenerate:

```bash
python bench/generate_scale_project.py --per-layer 250
```

SQL contains only constants / `ref()` — no hosts, tokens, or warehouse IDs.
