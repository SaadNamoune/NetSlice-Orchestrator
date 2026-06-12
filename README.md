# NetSlice-Orchestrator

**SDN-Based Dynamic Network Slicing with QoS Enforcement** — Mininet topology emulation + Ryu OpenFlow 1.3 controller implementing isolated network slices with bandwidth guarantees.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![OpenFlow 1.3](https://img.shields.io/badge/OpenFlow-1.3-orange)](https://opennetworking.org/)
[![Ryu SDN](https://img.shields.io/badge/controller-Ryu%204.x-green)](https://ryu-sdn.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Overview

Network slicing partitions a shared physical infrastructure into multiple isolated virtual networks, each with its own QoS guarantees. This project implements two-slice topology isolation using SDN:

- **Slice A (Premium)** — 10 Mbps guaranteed bandwidth, paths H1↔H3 via S2
- **Slice B (Standard)** — 1 Mbps guaranteed bandwidth, paths H2↔H4 via S3
- **Isolation** — strict MAC-based OpenFlow rules prevent cross-slice traffic
- **Monitoring** — real-time bandwidth and flow table metrics

---

## Architecture

```
                    ┌─────────────┐
         ┌──────────│  Ryu SDN    │──────────┐
         │          │  Controller  │          │
         │          └─────────────┘          │
         │  OpenFlow 1.3 / TCP 6633          │
         ▼                                   ▼
┌─────────────────────────────────────────────────────┐
│                  Mininet Topology                   │
│                                                     │
│  H1 ─┐         [S2] 10 Mbps Slice A        ┌─ H3  │
│      ├─ [S1] ──────────────────────── [S4] ─┤      │
│  H2 ─┘         [S3]  1 Mbps Slice B         └─ H4  │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Terminal 1 — Ryu controller
ryu-manager topology_slicing_controller.py

# Terminal 2 — Mininet topology
sudo python3 topology.py

# Bandwidth test inside CLI
mininet> h1 iperf -s &
mininet> h3 iperf -c 10.0.0.1 -t 10
```

---

## Experiment Results

| Slice | Hosts | Path | Configured BW | Measured BW | Isolation |
|---|---|---|---|---|---|
| A (Premium) | H1 ↔ H3 | S1→S2→S4 | 10 Mbps | 9.8 Mbps | ✅ |
| B (Standard) | H2 ↔ H4 | S1→S3→S4 | 1 Mbps | 0.98 Mbps | ✅ |

Cross-slice ping H1→H4: **blocked** by OpenFlow isolation rules.

---

## Author

**Saad Namoune** — ESI Alger  
[GitHub](https://github.com/SaadNamoune)
