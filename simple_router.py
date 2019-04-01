"""
    EE 555 Project
	Wenhan Tang 1210637460
	Chenguang He 8977866134
	
    Enter the following command to run:
    $ ./pox.py log.level --DEBUG misc.simple_router misc.full_payload        
    
	This is a custom router that can support:
	ARP 
	Static Routing 
	ICMP
	
	The following functions use https://github.com/zhan849/ee555/blob/master/part1/router.py as reference.
"""


from pox.core import core
import pox.openflow.libopenflow_01 as of

from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.packet.icmp import icmp
import pox.lib.packet as pkt
from pox.lib.addresses import IPAddr, EthAddr

import struct

log = core.getLogger()

Valid_IP = ['10.0.1.1', '10.0.1.100', '10.0.2.1', '10.0.2.100', '10.0.3.1', '10.0.3.100']


class Router (object):
    def __init__ (self, fakeways = []):
        log.debug('router registered')

	#import Ethernet Address
        self.fakeways = fakeways

	#clear ARP tabl, each cell has IP corresponding to MAC address
        self.arpTable = {}

        #clear routing table, each cell has IP corresponding to port
        self.routingTable = {}

        #clear connection
        self.connections = {}

        #clear ARP waiting line
        self.arpWait = {}

	#store IP to port and IP to MAC
	self.mac_to_port = {}
	self.ip_to_port = {}
		
	#add my self as listener in openflow
        core.openflow.addListeners(self)
        

    def _handle_GoingUpEvent (self, event):
        self.listenTo(core.openflow)
        #log.debug("Router UP" )

    def _handle_ConnectionUp(self, event): #open the connection
	"""
	For both Up and Down, we need to refresh connection information
	But in case DOWN, we need to clear ARP information
	"""
        log.debug("Connection %d is UP" % event.dpid)
	self.mac_to_port[event.dpid] = {}
	self.ip_to_port[event.dpid] = {}
	#self.arpTable[event.dpid] = {}
	self.routingTable[event.dpid] = {}
	#self.arpWait[event.dpid] = {}

    def _handle_ConnectionDown(self, event): #close the connection
        log.debug("Connection %d is DOWN" % event.dpid)
        self.routingTable[event.dpid] = {}
        self.connections[event.dpid] = {}
	self.ip_to_port[event.dpid] = {}
	self.mac_to_port[event.dpid] = {}
	
	#ARP need to cleared when the connection is closed
	self.arpTable[event.dpid] = {}
	self.arpWait[event.dpid] = {}

    #this function is for handling arp packets, it tells users whether it is added to arptable, or it is a invalid request
    def _handle_arp_packet(self, a, inport, dpid, packet_in):  
        log.debug("DPID : ARP packet, INPORT %d,  ARP  %s -> %s" %(inport, str(a.protosrc), str(a.protodst)))
	
        if a.prototype == arp.PROTO_TYPE_IP:
            if (a.hwtype == arp.HW_TYPE_ETHERNET) and (a.protosrc != 0):
		if a.protosrc not in self.arpTable[dpid]:
		    self.arpTable[dpid][a.protosrc] = a.hwsrc #add arp table if no record
                    log.debug('DPID : Added arpTable: ip = %s, mac = %s' % (str(a.protosrc), str(a.hwsrc)))
                    if (a.protosrc in self.arpWait[dpid]) and (len(self.arpWait[dpid][a.protosrc]) != 0):#waiting line is not empty
                        self._handle_arp_wait(dpid, a.protosrc)

	    if (a.opcode == arp.REQUEST) and (a.protodst in self.fakeways):
	    	self._handle_arp_response(a, inport, dpid)#reply arp broadcast
        else:
            log.error("DPID: Invalid ARP request")
	    return
    
    #this function is specifically for forming a waitlist for arp packets, when there is available, send the packet out
    def _handle_arp_wait(self, dpid, ip):
        log.debug('DPID : Pending packet in ARP wait line, ip %s' % (str(ip)))
        while len(self.arpWait[dpid][ip]) > 0: #renew packet in arp wait list every time, and delete the first one
            (bid, inport) = self.arpWait[dpid][ip][0]
            msg = of.ofp_packet_out(buffer_id=bid, in_port=inport)
            msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][ip]))
            msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][ip]))
            self.connections[dpid].send(msg)
            log.debug("DPID : Sending arp wait packet, destip: %s, destmac: %s, output port: %d" % (str(ip), str(self.arpTable[dpid][ip]), self.routingTable[dpid][ip]))
            del self.arpWait[dpid][ip][0]

    #this function is for handling arp response, it collect arp packets and examine their path, send response out
    def _handle_arp_response(self, a, inport, dpid):
        r = arp() #r is rountingtable, a is arptable
        r.hwtype = a.hwtype
        r.prototype = a.prototype
        r.hwlen = a.hwlen
        r.protolen = a.protolen
        r.opcode = arp.REPLY
        r.hwdst = a.hwsrc
        r.protodst = a.protosrc
        r.protosrc = a.protodst
        r.hwsrc = self.arpTable[dpid][a.protodst]
        
        e = ethernet(type=ethernet.ARP_TYPE, src=self.arpTable[dpid][a.protodst], dst=a.hwsrc)
        e.set_payload(r)
        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
        msg.in_port = inport

        log.debug("DPID : INPORT %d, answer for arp from %s: MAC for %s is %s" % (inport, str(a.protosrc), str(r.protosrc), str(r.hwsrc)))
        self.connections[dpid].send(msg)

    
    #this function si for handling arp request, it read arp packets and send request out accordingly
    def _handle_arp_request(self, packet, inport, dpid):
        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.hwlen = 6
        r.protolen = r.protolen
        r.opcode = r.REQUEST
        r.hwdst = ETHER_BROADCAST
        r.protodst = packet.next.dstip 
        r.hwsrc = packet.src            
        r.protosrc = packet.next.srcip  
        e = ethernet(type=ethernet.ARP_TYPE, src=packet.src,
                     dst=ETHER_BROADCAST)
        e.set_payload(r)
        log.debug("DPID : INPORT %d, sending ARP Request for %s on behalf of %s" % (inport, str(r.protodst), str(r.protosrc)))
        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        msg.in_port = inport
        self.connections[dpid].send(msg)
    
    #this function is for handling icmp rely, and send out the reply to router
    def _handle_icmp_reply(self, dpid, p, srcip, dstip, icmp_type):
        p_icmp = icmp()
        p_icmp.type = icmp_type
        if icmp_type == pkt.TYPE_ECHO_REPLY:
            p_icmp.payload = p.find('icmp').payload
        elif icmp_type == pkt.TYPE_DEST_UNREACH:
            orig_ip = p.find('ipv4')
            d = orig_ip.pack()
            d = d[:orig_ip.hl * 4 + 8]
            d = struct.pack("!HH", 0, 0) + d 
            p_icmp.payload = d
        
        p_ip = ipv4()
        p_ip.protocol = p_ip.ICMP_PROTOCOL
        p_ip.srcip = dstip 
        p_ip.dstip = srcip
        

        e = ethernet()
        e.src = p.dst
        e.dst = p.src
        e.type = e.IP_TYPE
        
        p_ip.payload = p_icmp
        e.payload = p_ip
        
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
        msg.data = e.pack()
        msg.in_port = self.routingTable[dpid][srcip]
        self.connections[dpid].send(msg)
        log.debug('DPID : IP %s pings router at %s, send icmp reply'% (str(srcip), str(dstip)))

    #this function is for handling incoming packets
    def _handle_PacketIn (self, event):
        packet = event.parsed 
        dpid = event.connection.dpid
        inport = event.port
        
	if dpid not in self.connections: #new host added
		self.connections[dpid] = event.connection
		self.routingTable[dpid] = {}
		self.arpWait[dpid] = {}
		self.arpTable[dpid] = {}
		for i in self.fakeways:
			self.arpTable[dpid][i] = EthAddr("%012x" % (dpid & 0xffffffffffff | 0x0000000000f0,)) #generate MAC for switch

        #packet is not right version
        if not packet.parsed:
            log.error("Incomplete packet")
            return


        packet_in = event.ofp # The actual ofp_packet_in message.
        p_n = packet.next

 	#The input packet contain ipv4 address data
        if isinstance(p_n, ipv4):
            log.debug('DPID : IPv4 Packet, Ienter from port %d, IP %s to %s'% (inport, p_n.srcip, p_n.dstip))
            
	    if p_n.srcip not in self.routingTable[dpid]:
		self.routingTable[dpid][p_n.srcip] = inport
		log.debug('DPID : Added IP %s into routing Table, output port %d, ipv4'% (str(p_n.srcip), inport))
            else:
                log.debug('DPID : IP %s,  output port %d, ipve' % (str(p_n.srcip), inport) )

	    if not p_n.dstip in Valid_IP:
		log.error('DPID : Invalid IP address')
		return
            if p_n.dstip in self.fakeways:
                #packet destined to the router
                if (isinstance(p_n.next, icmp)) and(p_n.next.type == pkt.TYPE_ECHO_REQUEST):
                    log.debug("packet to router")
                    self._handle_icmp_reply(dpid, packet, p_n.srcip, p_n.dstip, pkt.TYPE_ECHO_REPLY)
                        
            else:
                # need to check ARP
                if (p_n.dstip not in self.routingTable[dpid]) or (p_n.dstip not in self.arpTable[dpid]):
                    # cache it and send ARP request
                    if p_n.dstip not in self.arpWait[dpid]:
                        self.arpWait[dpid][p_n.dstip] = []
                    entry = (packet_in.buffer_id, inport)
                    self.arpWait[dpid][p_n.dstip].append(entry)
                    log.debug('DPID  : Packet %s to %s, add in ARP wait and send broadcast' % (str(p_n.srcip), str(p_n.dstip)))
                    self._handle_arp_request(packet, inport, dpid)
                else: #packet path only
                    msg = of.ofp_packet_out(buffer_id=packet_in.buffer_id, in_port=inport)
                    msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][p_n.dstip]))
                    msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][p_n.dstip]))
                    self.connections[dpid].send(msg)
                    log.debug('DPID : Packet %s to %s through port %d'% (str(p_n.srcip), str(p_n.dstip), self.routingTable[dpid][p_n.dstip]))
		    msg = of.ofp_flow_mod()
		    msg.match.dl_type = 0x800 
		    msg.match.nw_dst = p_n.dstip
        	    msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][p_n.dstip]))
        	    msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][p_n.dstip]))
        	    self.connections[dpid].send(msg)

        elif isinstance(p_n, arp): #The packet request ARP service
           
            if p_n.protosrc not in self.routingTable[dpid]:
		self.routingTable[dpid][p_n.protosrc] = inport
		log.debug('DPID : Added IP %s into routing Table to port %d, arp' % (str(p_n.protosrc), inport))
            else:
                log.debug('DPID : IP %s , output port %d, arp' % (str(p_n.protosrc), inport) )

	    if not p_n.protodst in Valid_IP:
		log.error('DPID : Invalid IP address')
		return
            self._handle_arp_packet(p_n, inport, dpid, packet_in)


	
def launch ():

    gateways = ['10.0.1.1', '10.0.2.1', '10.0.3.1']
    fakeways = [IPAddr(x) for x in gateways]
    core.registerNew(Router, fakeways)
