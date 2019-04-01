'''
    EE 555 Project
    Wenhan Tang 1210637460
    Chenguang He 8977866134
	
    Enter the following command to run:
    $ sudo mn --custom part1_topo.py --topo Part1_Topo --mac --controller=remote,ip=127.0.0.1
	
    This file contains necessary topology for router_part1.py 
	
    Three hosts h1 h2 h3 connect to switch s1.
    Three hosts don't have links with each other but only with the switch.
    Each host is configured with a subnet, IP, gateway and netmask.
'''
from mininet.topo import Topo

class Part1_Topo( Topo ):

    def __init__( self ):
        "Create custom topo."
        # Initialize topology
        Topo.__init__( self )

		#Add hosts and switches
        host1 = self.addHost( 'h1', ip="10.0.1.100/24", defaultRoute = "via 10.0.1.1" )
	host2 = self.addHost( 'h2', ip="10.0.2.100/24", defaultRoute = "via 10.0.2.1" )
	host3 = self.addHost( 'h3', ip="10.0.3.100/24", defaultRoute = "via 10.0.3.1" )
            
        switch = self.addSwitch('s1')

		#Add links
        self.addLink( host1, switch)
	self.addLink( host2, switch)
	self.addLink( host3, switch)
	
topos = { 'Part1_Topo': (lambda: Part1_Topo() ) }
