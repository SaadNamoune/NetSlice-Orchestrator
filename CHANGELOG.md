# Changelog

## [2.0.0] — 2024-06-12

### Added
- `monitor.py` — real-time BandwidthMonitor Ryu app (OFPPortStats every 5s)
- `qos_controller.py` — QoSSlicingController with OpenFlow metering (hard rate caps)
- `tests/test_slicing.py` — slice assignment and isolation unit tests
- `ARCHITECTURE.md` — topology diagram, OpenFlow rule tables, metering design
- `requirements.txt` — pinned dependencies
- `LICENSE` — MIT, copyright Saad Namoune 2024
- GitHub Actions CI pipeline

### Changed
- README rewritten as NetSlice-Orchestrator with benchmark results
- Topology comments translated from Italian to English

## [1.0.0] — 2024-01-01

Initial NCI lab — Mininet topology + Ryu slicing controller.
