# Changelog

## CSP-1 v2.0 — March 2026

### Added
- Cross-model validation: Claude Sonnet 4.6 (100%), GPT-4o (93%), Gemini 1.5 Flash (100%)
- V3 skill caching scaled to n=100: 88/100 vs 54/100, +63.0% lift, 0 regressions
- tools/fp_create.py — CLI to generate .fp files
- tests/cross_model/convoseed_ab_test.py — multi-model A/B test harness
- tests/v2_style_ab/convoseed_ab_test.jsx — browser style test
- tests/v3_skill_cache/csp1_task_test_v2.jsx — hard task skill cache test (n=100)
- docs/abstract.md — arXiv abstract draft

### Changed
- License: MIT → Apache 2.0
- Performance attribution clarified: gains come from summary.txt injection, not HDC encoding
- HDC encoder correctly scoped to speaker identification and retrieval only

### Removed / Killed
- "12.7% lift" claim — was Gemma3:1b vs 12b model size comparison, not FP vs no-FP
- V3 Run 1 easy tasks — 96% baseline ceiling effect, invalidated

## CSP-1 v1.0 — February 2026
- Initial proof of concept
- Speaker identification: p < 10⁻¹⁰⁰ across 1,000 trials on 524-message conversation
- Single-model style preservation: 87% win rate (Claude only)
