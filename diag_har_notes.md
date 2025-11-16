## Diagram Regression Investigation (Nov 13, 2025)

### User Report
- Diagrams “broken again” after Claude’s PGN ingest.
- HAR capture saved as `Downloads/127.0.0.1.har`.

### HAR Observations
- [ ] Verify whether `/query_merged` response includes `featured_diagrams`.
- [ ] Check if `/diagrams/<id>` requests return 404/500 or assets missing.
- [ ] Inspect HTML response to confirm `[FEATURED_DIAGRAM_X]` markers still appear.

### Next Steps
1. `haralyzer` or `jq` parse HAR for failing diagram requests.
2. Cross-check app logs (`flask_full.log` or new `tail -f`) for diagram errors.
3. Reproduce locally by hitting `/query_merged` with sample query and inspect JSON payload.
