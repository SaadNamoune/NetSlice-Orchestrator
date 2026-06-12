"""QoS-aware Ryu controller — extends topology slicing with DSCP remarking and metering."""
from __future__ import annotations
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3


SLICE_A_BW_KBPS = 10_000
SLICE_B_BW_KBPS = 1_000


class QoSSlicingController(app_manager.RyuApp):
    """Extends TopologySlicingController with OpenFlow metering for hard rate limits."""
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.h1_mac = "00:00:00:00:00:01"
        self.h2_mac = "00:00:00:00:00:02"
        self.h3_mac = "00:00:00:00:00:03"
        self.h4_mac = "00:00:00:00:00:04"

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self._install_meters(datapath)

    def _install_meters(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # Meter 1 — Slice A cap
        bands_a = [parser.OFPMeterBandDrop(rate=SLICE_A_BW_KBPS, burst_size=512)]
        mod_a = parser.OFPMeterMod(datapath, ofproto.OFPMC_ADD, ofproto.OFPMF_KBPS, 1, bands_a)
        datapath.send_msg(mod_a)
        # Meter 2 — Slice B cap
        bands_b = [parser.OFPMeterBandDrop(rate=SLICE_B_BW_KBPS, burst_size=128)]
        mod_b = parser.OFPMeterMod(datapath, ofproto.OFPMC_ADD, ofproto.OFPMF_KBPS, 2, bands_b)
        datapath.send_msg(mod_b)
        self.logger.info("Meters installed on dpid=%s", datapath.id)

    def add_flow_with_meter(self, datapath, priority, match, actions, meter_id):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [
            parser.OFPInstructionMeter(meter_id),
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
        ]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
