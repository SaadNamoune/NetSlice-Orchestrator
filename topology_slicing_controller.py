from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

class TopologySlicingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TopologySlicingController, self).__init__(*args, **kwargs)
        self.h1_mac = '00:00:00:00:00:01'
        self.h2_mac = '00:00:00:00:00:02'
        self.h3_mac = '00:00:00:00:00:03'
        self.h4_mac = '00:00:00:00:00:04'

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # Mappatura delle porte (importante per il debug)
        # s1: h1=1, h2=2, s2=3, s3=4
        # s2: s1=1, s4=2
        # s3: s1=1, s4=2
        # s4: h3=1, h4=2, s2=3, s3=4
        
        # Gestione ARP (bassa priorità, per la scoperta degli host)
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 1, match_arp, actions_arp)

        # --- Switch S1 (Punto di ingresso) ---
        if dpid == 1:
            # SLICE SUPERIORE: H1 <-> H3 via S2
            self.add_path(parser, datapath, in_port=1, out_port=3, src_mac=self.h1_mac, dst_mac=self.h3_mac) # H1 -> S2
            self.add_path(parser, datapath, in_port=3, out_port=1, src_mac=self.h3_mac, dst_mac=self.h1_mac) # S2 -> H1

            # SLICE INFERIORE: H2 <-> H4 via S3
            self.add_path(parser, datapath, in_port=2, out_port=4, src_mac=self.h2_mac, dst_mac=self.h4_mac) # H2 -> S3
            self.add_path(parser, datapath, in_port=4, out_port=2, src_mac=self.h4_mac, dst_mac=self.h2_mac) # S3 -> H2

        # --- Switch S2 (Core Slice Superiore) ---
        elif dpid == 2:
            self.add_path(parser, datapath, in_port=1, out_port=2, src_mac=self.h1_mac, dst_mac=self.h3_mac) # S1 -> S4
            self.add_path(parser, datapath, in_port=2, out_port=1, src_mac=self.h3_mac, dst_mac=self.h1_mac) # S4 -> S1
            
        # --- Switch S3 (Core Slice Inferiore) ---
        elif dpid == 3:
            self.add_path(parser, datapath, in_port=1, out_port=2, src_mac=self.h2_mac, dst_mac=self.h4_mac) # S1 -> S4
            self.add_path(parser, datapath, in_port=2, out_port=1, src_mac=self.h4_mac, dst_mac=self.h2_mac) # S4 -> S1

        # --- Switch S4 (Punto di uscita) ---
        elif dpid == 4:
            # SLICE SUPERIORE: H1 <-> H3 via S2
            self.add_path(parser, datapath, in_port=3, out_port=1, src_mac=self.h1_mac, dst_mac=self.h3_mac) # S2 -> H3
            self.add_path(parser, datapath, in_port=1, out_port=3, src_mac=self.h3_mac, dst_mac=self.h1_mac) # H3 -> S2

            # SLICE INFERIORE: H2 <-> H4 via S3
            self.add_path(parser, datapath, in_port=4, out_port=2, src_mac=self.h2_mac, dst_mac=self.h4_mac) # S3 -> H4
            self.add_path(parser, datapath, in_port=2, out_port=4, src_mac=self.h4_mac, dst_mac=self.h2_mac) # H4 -> S3

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
        
    def add_path(self, parser, datapath, in_port, out_port, src_mac, dst_mac):
        """ Funzione di utilità per aggiungere una regola di flusso IP/ICMP """
        # Regola per traffico IP
        match_ip = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_src=src_mac, eth_dst=dst_mac)
        actions = [parser.OFPActionOutput(out_port)]
        self.add_flow(datapath, 10, match_ip, actions)