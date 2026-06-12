#!/usr/bin/python3
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
 
# --- Costanti/protocolli
IP_PROTO_ICMP = 1
IP_PROTO_TCP  = 6
IP_PROTO_UDP  = 17
VIDEO_PORT    = 9999
 
# --- Priorità
PRIO_LOCAL      = 60
PRIO_ARP        = 50
PRIO_VIDEO      = 40      # regole video
PRIO_NON_VIDEO  = 30      # regole non-video (icmp/tcp/udp!=9999)
PRIO_GUARD      = 20      # regole "guardia" per evitare leak
PRIO_DROP       = 0       # table-miss = drop
 
class SliceController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
 
    # helper per installare flow
    def add_flow(self, dp, prio, match, actions):
        p, ofp = dp.ofproto_parser, dp.ofproto
        inst = [p.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(p.OFPFlowMod(datapath=dp, priority=prio, match=match, instructions=inst))
 
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp  = ev.msg.datapath
        ofp = dp.ofproto
        p   = dp.ofproto_parser
        dpid = dp.id
        # Mappa porte (coerente con la topologia del progetto)
        # S1: 1=H1, 2=H2, 3=S2 (upper), 4=S3 (lower)
        # S2: 1=S1, 2=S4     (upper slice)
        # S3: 1=S1, 2=S4     (lower slice)
        # S4: 1=H3, 2=H4, 3=S2 (upper), 4=S3 (lower)
 
        # --- Default: drop tutto
        self.add_flow(dp, PRIO_DROP, p.OFPMatch(), [])
 
        # --- ARP: flood ovunque
        self.add_flow(dp, PRIO_ARP, p.OFPMatch(eth_type=0x0806),
                      [p.OFPActionOutput(ofp.OFPP_FLOOD)])
 
        if dpid == 1:
            # ===== S1 (edge sinistra) =====
 
            # Traffico locale (H1 <-> H2) su S1
            self.add_flow(dp, PRIO_LOCAL,
                          p.OFPMatch(eth_type=0x0800, in_port=1, ipv4_dst="10.0.0.2"),
                          [p.OFPActionOutput(2)])
            self.add_flow(dp, PRIO_LOCAL,
                          p.OFPMatch(eth_type=0x0800, in_port=2, ipv4_dst="10.0.0.1"),
                          [p.OFPActionOutput(1)])
 
            # Host -> Core (TRAFFICO INIZIALE)
            # Video (UDP:9999) verso upper (porta 3)
            for inport in (1, 2):
                self.add_flow(dp, PRIO_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_UDP, udp_dst=VIDEO_PORT),
                              [p.OFPActionOutput(3)])
            # Non-video (ICMP/TCP/UDP!=9999) verso lower (porta 4)
            # ICMP
            for inport in (1, 2):
                self.add_flow(dp, PRIO_NON_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_ICMP),
                              [p.OFPActionOutput(4)])
            # TCP generico
            for inport in (1, 2):
                self.add_flow(dp, PRIO_NON_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_TCP),
                              [p.OFPActionOutput(4)])
            # UDP generico (senza la 9999 che è già catturata sopra)
            for inport in (1, 2):
                self.add_flow(dp, PRIO_GUARD,  # leggermente più bassa di PRIO_NON_VIDEO
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_UDP),
                              [p.OFPActionOutput(4)])
            # Fallback IPv4 (qualsiasi altro IPv4) -> lower
            for inport in (1, 2):
                self.add_flow(dp, PRIO_GUARD,
                              p.OFPMatch(eth_type=0x0800, in_port=inport),
                              [p.OFPActionOutput(4)])
 
            # Core -> Host (TRAFFICO DI RITORNO)
            # PRIORITÀ AUMENTATA A PRIO_LOCAL (60) PER STABILITÀ
            for inport in (3, 4):
                self.add_flow(dp, PRIO_LOCAL,
                              p.OFPMatch(eth_type=0x0800, in_port=inport, ipv4_dst="10.0.0.1"),
                              [p.OFPActionOutput(1)])
                self.add_flow(dp, PRIO_LOCAL,
                              p.OFPMatch(eth_type=0x0800, in_port=inport, ipv4_dst="10.0.0.2"),
                              [p.OFPActionOutput(2)])
 
        elif dpid == 2:
            # ===== S2 (upper slice = solo video) =====
            # Permetti SOLO UDP:9999 fra 1<->2
            self.add_flow(dp, PRIO_VIDEO,
                          p.OFPMatch(eth_type=0x0800, in_port=1,
                                     ip_proto=IP_PROTO_UDP, udp_dst=VIDEO_PORT),
                          [p.OFPActionOutput(2)])
            self.add_flow(dp, PRIO_VIDEO,
                          p.OFPMatch(eth_type=0x0800, in_port=2,
                                     ip_proto=IP_PROTO_UDP, udp_dst=VIDEO_PORT),
                          [p.OFPActionOutput(1)])
            # Tutto il resto resta droppato dal table-miss (PRIO_DROP)
 
        elif dpid == 3:
            # ===== S3 (lower slice = non-video) =====
            # (Opzionale) regola guardia: se per errore arriva UDP:9999 qui, lo drop
            self.add_flow(dp, PRIO_VIDEO,
                          p.OFPMatch(eth_type=0x0800, ip_proto=IP_PROTO_UDP, udp_dst=VIDEO_PORT),
                          [])  # azioni vuote = drop (priorità > PRIO_NON_VIDEO)
 
            # Permetti TUTTO l'IPv4 non-video 1<->2 (PRIO_NON_VIDEO)
            # Regole generiche IPv4 per semplificare la logica e prevenire drop
            # Traffico S1 -> S4
            self.add_flow(dp, PRIO_NON_VIDEO,
                          p.OFPMatch(eth_type=0x0800, in_port=1),
                          [p.OFPActionOutput(2)])
            # Traffico S4 -> S1
            self.add_flow(dp, PRIO_NON_VIDEO,
                          p.OFPMatch(eth_type=0x0800, in_port=2),
                          [p.OFPActionOutput(1)])
 
            # Le regole più specifiche (ICMP, TCP, UDP generico) con PRIO_NON_VIDEO e PRIO_GUARD
            # sono state rimosse da S3 perché la regola IPv4 generica (PRIO 30) le copre tutte
            # e S3 non deve fare distinzioni, solo inoltrare ciò che non è Video.
 
        elif dpid == 4:
            # ===== S4 (edge destra) =====
 
            # Traffico locale (H3 <-> H4)
            self.add_flow(dp, PRIO_LOCAL,
                          p.OFPMatch(eth_type=0x0800, in_port=1, ipv4_dst="10.0.0.4"),
                          [p.OFPActionOutput(2)])
            self.add_flow(dp, PRIO_LOCAL,
                          p.OFPMatch(eth_type=0x0800, in_port=2, ipv4_dst="10.0.0.3"),
                          [p.OFPActionOutput(1)])
 
            # Host -> Core (TRAFFICO INIZIALE)
            # Video (UDP:9999) verso upper (porta 3)
            for inport in (1, 2):
                self.add_flow(dp, PRIO_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_UDP, udp_dst=VIDEO_PORT),
                              [p.OFPActionOutput(3)])
            # Non-video verso lower (porta 4)
            # ICMP
            for inport in (1, 2):
                self.add_flow(dp, PRIO_NON_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_ICMP),
                              [p.OFPActionOutput(4)])
            # TCP
            for inport in (1, 2):
                self.add_flow(dp, PRIO_NON_VIDEO,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_TCP),
                              [p.OFPActionOutput(4)])
            # UDP generico
            for inport in (1, 2):
                self.add_flow(dp, PRIO_GUARD,
                              p.OFPMatch(eth_type=0x0800, in_port=inport,
                                         ip_proto=IP_PROTO_UDP),
                              [p.OFPActionOutput(4)])
            # Fallback IPv4
            for inport in (1, 2):
                self.add_flow(dp, PRIO_GUARD,
                              p.OFPMatch(eth_type=0x0800, in_port=inport),
                              [p.OFPActionOutput(4)])
 
            # Core -> Host (TRAFFICO DI RITORNO)
            # PRIORITÀ AUMENTATA A PRIO_LOCAL (60) PER STABILITÀ
            for inport in (3, 4):
                self.add_flow(dp, PRIO_LOCAL,
                              p.OFPMatch(eth_type=0x0800, in_port=inport, ipv4_dst="10.0.0.3"),
                              [p.OFPActionOutput(1)])
                self.add_flow(dp, PRIO_LOCAL,
                              p.OFPMatch(eth_type=0x0800, in_port=inport, ipv4_dst="10.0.0.4"),
                              [p.OFPActionOutput(2)])
 
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        # Nessun learning: tutto è gestito da flow statiche
        return
 