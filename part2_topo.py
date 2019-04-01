'''
    EE 555 Project
    Wenhan Tang 1210637460
    Chenguang He 8977866134
	
    Enter the following command to run:
    $ sudo mn --custom part2_topo.py --topo Part2_Topo --mac --controller=remote,ip=127.0.0.1
	
    This file contains necessary topology for router_part2.py 
	
    Three hosts h3 h4 h5 connect to two switches s1 and s2.
    Three hosts don't have links with each other but only with the switch.
    Switches have links connect with each other.
    Hosts h3 h4 are connected with switch s1 while host h5 is connected with switch s2.
    Each host is configured with a subnet, IP, gateway and netmask.
'''
from mininet.topo import Topo

class Part2_Topo( Topo ):

    def __init__( self ):
        "Create custom topo."
		
        # Initialize topology
        Topo.__init__( self )
		
	#Add hosts and switches
        host3 = self.addHost( 'h3', ip="10.0.1.2/24", defaultRoute = "via 10.0.1.1" )
	host4 = self.addHost( 'h4', ip="10.0.1.3/24", defaultRoute = "via 10.0.1.1" )
	host5 = self.addHost( 'h5', ip="10.0.2.2/24", defaultRoute = "via 10.0.2.1" )
            
        switch1 = self.addSwitch( 's1' )
	switch2 = self.addSwitch( 's2' ) 

		
	#Add links
        self.addLink( host3, switch1, port1=1, port2=2 )
	self.addLink( host4, switch1, port1=1, port2=3 )
	self.addLink( host5, switch2, port1=1, port2=2 )
	self.addLink( switch1, switch2, port1=1, port2=1 )

topos = { 'Part2_Topo': (lambda: Part2_Topo() ) }

