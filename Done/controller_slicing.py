#!/usr/bin/python3
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

class SliceController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SliceController, self).__init__(*args, **kwargs)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=0, hard_timeout=0)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id  # 1=S1, 2=S2, 3=S3, 4=S4

        # 0. Default: DROP (Priorità 0) - Blocca tutto ciò che non ha una regola specifica
        match = parser.OFPMatch()
        self.add_flow(datapath, 0, match, [])

        # ATTENZIONE: La regola ARP generica FLOOD è stata RIMOSSA per isolare l'ARP
        # e velocizzare la risoluzione nei percorsi consentiti.

        # MAC Host
        H1 = "00:00:00:00:00:01"
        H2 = "00:00:00:00:00:02"
        H3 = "00:00:00:00:00:03"
        H4 = "00:00:00:00:00:04"

        # Riferimento Porte: S1(1=H1, 2=H2, 3=S2, 4=S3), S2(1=S1, 2=S4), S3(1=S1, 2=S4), S4(1=H3, 2=H4, 3=S2, 4=S3)

        # S1 (Ponte verso entrambe le slice)
        if dpid == 1:
            # --- RULES ARP (Priorità 50) ---
            # H1 <-> H3 (upper slice, porta 1 <-> 3)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=1), [parser.OFPActionOutput(3)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=3), [parser.OFPActionOutput(1)])
            # H2 <-> H4 (lower slice, porta 2 <-> 4)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=2), [parser.OFPActionOutput(4)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=4), [parser.OFPActionOutput(2)])

            # --- RULES IP (Priorità 30) ---
            # H1 -> H3
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=1, eth_src=H1, eth_dst=H3),
                [parser.OFPActionOutput(3)])
            # H3 -> H1
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=3, eth_src=H3, eth_dst=H1),
                [parser.OFPActionOutput(1)])
            # H2 -> H4
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=2, eth_src=H2, eth_dst=H4),
                [parser.OFPActionOutput(4)])
            # H4 -> H2
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=4, eth_src=H4, eth_dst=H2),
                [parser.OFPActionOutput(2)])

        # S2 (Upper slice centrale)
        elif dpid == 2:
            # --- RULES ARP (Priorità 50) ---
            # S1 <-> S4 (Upper)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=1), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=2), [parser.OFPActionOutput(1)])

            # --- RULES IP (Priorità 30) ---
            # H1 -> H3
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=1, eth_src=H1, eth_dst=H3),
                [parser.OFPActionOutput(2)])
            # H3 -> H1
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=2, eth_src=H3, eth_dst=H1),
                [parser.OFPActionOutput(1)])

        # S3 (Lower slice centrale)
        elif dpid == 3:
            # --- RULES ARP (Priorità 50) ---
            # S1 <-> S4 (Lower)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=1), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=2), [parser.OFPActionOutput(1)])

            # --- RULES IP (Priorità 30) ---
            # H2 -> H4
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=1, eth_src=H2, eth_dst=H4),
                [parser.OFPActionOutput(2)])
            # H4 -> H2
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=2, eth_src=H4, eth_dst=H2),
                [parser.OFPActionOutput(1)])

        # S4 (Ponte verso entrambe le slice)
        elif dpid == 4:
            # --- RULES ARP (Priorità 50) ---
            # SLICE SUPERIORE: H1 <-> H3 (porta 3 <-> 1)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=3), [parser.OFPActionOutput(1)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=1), [parser.OFPActionOutput(3)])
            # SLICE INFERIORE: H2 <-> H4 (porta 4 <-> 2)
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=4), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 50, parser.OFPMatch(eth_type=0x0806, in_port=2), [parser.OFPActionOutput(4)])

            # --- SLICE SUPERIORE: H1 <-> H3 (Priorità 30) ---
            # H1 -> H3
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=3, eth_src=H1, eth_dst=H3),
                [parser.OFPActionOutput(1)])
            # H3 -> H1
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=1, eth_src=H3, eth_dst=H1),
                [parser.OFPActionOutput(3)])

            # --- SLICE INFERIORE: H2 <-> H4 (Priorità 30) ---
            # H2 -> H4
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=4, eth_src=H2, eth_dst=H4),
                [parser.OFPActionOutput(2)])
            # H4 -> H2
            self.add_flow(datapath, 30,
                parser.OFPMatch(eth_type=0x0800, in_port=2, eth_src=H4, eth_dst=H2),
                [parser.OFPActionOutput(4)])


  