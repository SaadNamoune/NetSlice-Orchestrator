#!/usr/bin/python3

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_topology():
    """
    Crea la topologia di rete per il progetto di slicing.
    """
    # Crea una nuova rete Mininet pulita
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )

    info("### Aggiungo il controller remoto\n")
    # IP del controller, di default Ryu gira sulla porta 6633 sulla macchina locale
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    info("### Aggiungo gli host\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')

    info("### Aggiungo gli switch\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')

    info("### Creo i collegamenti\n")
    # Collegamenti Host -> Switch
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s4)
    net.addLink(h4, s4)

    # Slice Superiore (10 Mbps)
    net.addLink(s1, s2, bw=10)
    net.addLink(s2, s4, bw=10)

    # Slice Inferiore (1 Mbps)
    net.addLink(s1, s3, bw=1)
    net.addLink(s3, s4, bw=1)

    info("### Avvio la rete\n")
    net.build()
    net.start()

    info("### Avvio la Command Line Interface (CLI) di Mininet\n")
    CLI(net)

    info("### Fermo la rete\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()