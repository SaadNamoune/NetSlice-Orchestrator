#!/usr/bin/python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.link import TCLink

class PdfFigureTopo(Topo):
    def build(self):
        # Host (MAC fissati per coerenza con il controller che faremo dopo)
        h1 = self.addHost('h1', mac="00:00:00:00:00:01")
        h2 = self.addHost('h2', mac="00:00:00:00:00:02")
        h3 = self.addHost('h3', mac="00:00:00:00:00:03")
        h4 = self.addHost('h4', mac="00:00:00:00:00:04")

        # Switch (OpenFlow 1.3)
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', protocols='OpenFlow13')

        # Collegamenti host<->edge
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s4)
        self.addLink(h4, s4)

        # Upper slice (10 Mbps): S1—S2—S4
        self.addLink(s1, s2, bw=10)  # 10 Mbps come nel PDF
        self.addLink(s2, s4, bw=10)

        # Lower slice (1 Mbps): S1—S3—S4
        self.addLink(s1, s3, bw=1)   # 1 Mbps come nel PDF
        self.addLink(s3, s4, bw=1)

if __name__ == '__main__':
    net = Mininet(
        topo=PdfFigureTopo(),
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
        switch=OVSSwitch,
        link=TCLink,      # necessario per usare i parametri bw
        autoSetMacs=True  # comodo in fase di test
    )
    for sw in net.switches:
        sw.cmd('ovs-vsctl set bridge %s protocols=OpenFlow13' % sw.name)
    net.start()
    CLI(net)
    net.stop()
