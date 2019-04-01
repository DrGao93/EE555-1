'''
    EE 555 Project
    Wenhan Tang 1210637460
    Chenguang He 8977866134
    
    Enter the following command to run:
    $ sudo mn --custom bonus_topo.py --topo Bonus_Topo --mac --controller=remote,ip=127.0.0.1

    This file contains necessary topology for the bonus part

    Ten hosts h1-h10 connect to four switches s1-s4.
    Ten hosts don't have links with each other but only with the switch.
    Switch s1 is connected to switch s2, switch s2 is connected to switch s1 s3, switch s3 is connected to switch s2 s4, switch s4 is connected to switch s3.
    Hosts h1 h2 h3 are connected with switch s1, hosts h4 h5 are connected with switch s2, hosts h6 h7 are connected with switch s3, hosts h8 h9 h10 are connected with switch s4.
    Each host is configured with a subnet, IP, gateway and netmask.
'''

from mininet.topo import Topo

class Bonus_Topo( Topo ):

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

	#Add hosts and switches 
        host1 = self.addHost( 'h1', ip='10.0.1.2/24', defaultRoute = 'via 10.0.1.1' )
        host2 = self.addHost( 'h2', ip='10.0.1.3/24', defaultRoute = 'via 10.0.1.1' )
        host3 = self.addHost( 'h3', ip='10.0.1.4/24', defaultRoute = 'via 10.0.1.1' )
        host4 = self.addHost( 'h4', ip='10.0.2.2/24', defaultRoute = 'via 10.0.2.1' )
        host5 = self.addHost( 'h5', ip='10.0.2.3/24', defaultRoute = 'via 10.0.2.1' )
        host6 = self.addHost( 'h6', ip='10.0.3.2/24', defaultRoute = 'via 10.0.3.1' )
        host7 = self.addHost( 'h7', ip='10.0.3.3/24', defaultRoute = 'via 10.0.3.1' )
        host8 = self.addHost( 'h8', ip='10.0.4.2/24', defaultRoute = 'via 10.0.4.1' )
        host9 = self.addHost( 'h9', ip='10.0.4.3/24', defaultRoute = 'via 10.0.4.1' )
        host10 = self.addHost( 'h10', ip='10.0.4.4/24', defaultRoute = 'via 10.0.4.1' )

        switch1 = self.addSwitch( 's1' ) 
        switch2 = self.addSwitch( 's2' ) 
        switch3 = self.addSwitch( 's3' ) 
        switch4 = self.addSwitch( 's4' )
	
	#Add links
        self.addLink( 's1', 's2', port1=1, port2=1 ) 
        self.addLink( 's2', 's3', port1=2, port2=1 ) 
        self.addLink( 's3', 's4', port1=2, port2=1 ) 
        self.addLink( 'h1', 's1', port1=1, port2=2 ) 
        self.addLink( 'h2', 's1', port1=1, port2=3 ) 
        self.addLink( 'h3', 's1', port1=1, port2=4 ) 
        self.addLink( 'h4', 's2', port1=1, port2=3 ) 
        self.addLink( 'h5', 's2', port1=1, port2=4 ) 
        self.addLink( 'h6', 's3', port1=1, port2=3 ) 
        self.addLink( 'h7', 's3', port1=1, port2=4 ) 
        self.addLink( 'h8', 's4', port1=1, port2=2 ) 
        self.addLink( 'h9', 's4', port1=1, port2=3 ) 
        self.addLink( 'h10', 's4', port1=1, port2=4 ) 
        

topos = { 'Bonus_Topo': (lambda: Bonus_Topo() ) }
