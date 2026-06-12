# Architecture — NetSlice-Orchestrator

## Topology

```
H1 (10.0.0.1) ─┐                              ┌─ H3 (10.0.0.3)
               ├─ S1 ─── S2 (10 Mbps) ─── S4 ─┤
H2 (10.0.0.2) ─┘    └─── S3 (1 Mbps)  ───┘    └─ H4 (10.0.0.4)
```

## Slice Definitions

| Slice | Hosts | Switch Path | BW | Priority |
|---|---|---|---|---|
| A | H1 ↔ H3 | S1 → S2 → S4 | 10 Mbps | HIGH |
| B | H2 ↔ H4 | S1 → S3 → S4 | 1 Mbps | STANDARD |

## OpenFlow Rules (S1, dpid=1)

| Priority | in_port | eth_src | eth_dst | action |
|---|---|---|---|---|
| 10 | 1 | H1_MAC | H3_MAC | output:3 (→S2) |
| 10 | 2 | H2_MAC | H4_MAC | output:4 (→S3) |
| 1 | * | * | * | FLOOD (ARP only) |

## QoS Metering (qos_controller.py)

OpenFlow 1.3 meters enforce hard rate caps at the datapath:
- Meter 1 → Slice A → DROP above 10,000 kbps
- Meter 2 → Slice B → DROP above 1,000 kbps

## Monitoring (monitor.py)

Port stats polled every 5s via `OFPPortStatsRequest`. Logs rx_bytes/tx_bytes per port per switch.
