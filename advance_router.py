"""
    EE 555 Project
    Wenhan Tang 1210637460
    Chenguang He 8977866134
	
    Enter the following command to run:
    $ ./pox.py log.level --DEBUG misc.advance_router misc.full_payload
	
    This is a custom router that can support:
	ARP 
	Static Routing 
	ICMP
	
	This part need to consider another network that is different from simple_router.py in part1
	
	The following functions use https://github.com/zhan849/ee555/blob/master/part2/router_part2.py as reference.
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
import time

log = core.getLogger()

DEFAULT_GATEWAY = 1
Valid_IP = [IPAddr('10.0.1.1'), IPAddr('10.0.1.2'), IPAddr('10.0.1.3'), IPAddr('10.0.2.1'), IPAddr('10.0.2.2'), IPAddr('10.0.2.3'), IPAddr('10.0.2.4')]
Subnet1 = ['10.0.1.1', '10.0.1.2', '10.0.1.3']
Subnet2 = ['10.0.2.1', '10.0.2.2', '10.0.2.3', '10.0.2.4']


# main router class
class Router (object):
    def __init__ (self):
        log.debug('router registered')
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
       
        #we have two router, so a table needed to store routere data
        self.routerIP = {}

        core.openflow.addListeners(self)


    # this event is for router registering at POX
    def _handle_GoingUpEvent (self, event):
        self.listenTo(core.openflow)
        log.debug("Router is UP" )

    # this event is for switch connecting to controller
    def _handle_ConnectionUp(self, event):
        log.debug("DPID %d is UP" % event.dpid)
        self.routerIP[event.dpid] = IPAddr('10.0.%d.1' % (event.dpid))
	
	if event.dpid not in self.connections:
    	    self.connections[event.dpid] = event.connection
	self.arpTable[event.dpid] = {}
	self.routingTable[event.dpid] = {}
	self.arpWait[event.dpid] = {}
        self.arpTable[event.dpid][IPAddr('10.0.%d.1' % (event.dpid))] = EthAddr("%012x" % (event.dpid & 0xffffffffffff | 0x0000000000f0,))
        if len(self.routerIP) == 2:
            self._handle_arp_request(IPAddr('10.0.%d.1' % (event.dpid)), IPAddr('10.0.%d.1' %(3-event.dpid)), EthAddr("%012x" % (event.dpid & 0xffffffffffff | 0x0000000000f0,)), of.OFPP_FLOOD, event.dpid)



    # this event is for switch disconnecting to controller
    def _handle_ConnectionDown(self, event):
        log.debug("DPID %d is DOWN, cleaning dp cache" % event.dpid)
        self.arpTable[event.dpid] = {}
        self.routingTable[event.dpid] = {}
	self.connections[event.dpid] = {}
        self.arpWait[event.dpid] = {}
        self.routerIP[event.dpid] = {}

    def _handle_arp_packet(self, a, inport, dpid, packet_in):
        log.debug("DPID %d: ARP packet, INPORT %d,  ARP %s => %s", dpid, inport, str(a.protosrc), str(a.protodst))


        if a.prototype == arp.PROTO_TYPE_IP:
            if a.hwtype == arp.HW_TYPE_ETHERNET and a.protosrc != 0:
                # learn the MAC
                if a.protosrc not in self.arpTable[dpid]:
                    self.arpTable[dpid][a.protosrc] = a.hwsrc
                    log.debug('DPID %d: added arpTable entry: ip = %s, mac = %s' % (dpid, str(a.protosrc), str(a.hwsrc)))
                    #print self.arpWait[dpid]
                    if a.protosrc in self.arpWait[dpid] and len(self.arpWait[dpid][a.protosrc]) != 0:
                        self._handle_arp_wait(dpid, a.protosrc)

                if a.opcode == arp.REQUEST:
                    if str(a.protodst) == str(self.routerIP[dpid]):
                        self._handle_arp_response(a, inport, dpid)
                    else:
			msg = of.ofp_packet_out()
			msg.data = packet_in
			msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD)) #boradcast the messgae if packet neeed to be resent with a nuknown address
			self.connections[dpid].send(msg)
                elif a.opcode == arp.REPLY and a.protodst != IPAddr('10.0.%d.1' % (dpid)):
                    # ARP request not to this ro
                        
		    msg = of.ofp_packet_out()
		    msg.data = packet_in
		    msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][a.protodst])) #send to port in routing Table if the known packet needed to be resent
		    self.connections[dpid].send(msg)
                            
        else:
            log.debug("DPID %d: Invalid ARP request" % (dpid))
	    
            #self._resend_packet (dpid, packet_in, of.OFPP_FLOOD)
	    msg = of.ofp_packet_out()
	    msg.data = packet_in
	    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
	    self.connections[dpid].send(msg)


    def _handle_arp_wait(self, dpid, ip):
        log.debug('DPID %d: processing pending arpWait packet for ip %s' % (dpid, str(ip)))
        while len(self.arpWait[dpid][ip]) > 0:
            (bid, inport) = self.arpWait[dpid][ip][0]
            msg = of.ofp_packet_out(buffer_id=bid, in_port=inport)
            msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][ip]))
            msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][ip]))
            self.connections[dpid].send(msg)
            log.debug("DPID %d: sending arp wait packet, destip: %s, destmac: %s, output port: %d" % (dpid, str(ip), str(self.arpTable[dpid][ip]), self.routingTable[dpid][ip]))
            del self.arpWait[dpid][ip][0]

    def _handle_arp_response(self, a, inport, dpid):
        r = arp()
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

        log.debug("DPID %d, INPORT %d, answering for arp from %s: MAC for %s is %s", dpid, inport, str(a.protosrc), str(r.protosrc), str(r.hwsrc))
        self.connections[dpid].send(msg)


    def _handle_arp_request(self, srcip, dstip, srcmac, inport, dpid):
        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.hwlen = 6
        #arp().protolen = arp().protolen
        r.opcode = r.REQUEST
        r.hwdst = ETHER_BROADCAST
        r.protodst = dstip                 
        r.hwsrc = srcmac                    
        r.protosrc = srcip                  
        e = ethernet(type=ethernet.ARP_TYPE, src=srcmac,dst=ETHER_BROADCAST)
        e.set_payload(r)
        log.debug("DPID %d, INPORT %d, sending ARP Request for %s on behalf of %s" % (dpid, inport, str(r.protodst), str(r.protosrc)))
        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        self.connections[dpid].send(msg)

    def _handle_icmp_reply(self, dpid, p, srcip, dstip, icmp_type):
        pic = icmp()
        pic.type = icmp_type
        if icmp_type == pkt.TYPE_ECHO_REPLY:
            pic.payload = p.find('icmp').payload
        elif icmp_type == pkt.TYPE_DEST_UNREACH:
            orig_ip = p.find('ipv4')
            d = orig_ip.pack()
            d = d[:orig_ip.hl * 4 + 8]
            d = struct.pack("!HH", 0, 0) + d 
            pic.payload = d

        
        #p_ip = ipv4()
        ipv4().protocol = ipv4().ICMP_PROTOCOL
        ipv4().srcip = dstip  
        ipv4().dstip = srcip
        

        e = ethernet()
        e.src = p.dst
        if (srcip in Subnet1 and self.routerIP[dpid] in Subnet1) or (srcip in Subnet2 and self.routerIP[dpid] in Subnet2):
            e.dst = p.src
        else:
            gatewayip = IPAddr('10.0.%d.1' % (3-dpid))
            e.dst = self.arpTable[dpid][gatewayip]

        e.type = e.IP_TYPE
        
        p_ip.payload = p_icmp
        e.payload = p_ip
        
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
        msg.data = e.pack()
        msg.in_port = self.routingTable[dpid][srcip]
        self.connections[dpid].send(msg)
        log.debug('DPID %d: IP %s pings router at %s, generating icmp reply', dpid, str(srcip), str(dstip))

    def _handle_PacketIn (self, event):
        packet = event.parsed #This is the parsed packet data.
        dpid = event.connection.dpid
        inport = event.port

        packet_in = event.ofp #The actual ofp_packet_in message.
        n = packet.next

        # deal with different packets
        if isinstance(n, ipv4):
            log.debug('DPID %d: IPv4 Packet, INPORT %d, IP %s => %s', dpid, inport, packet.next.srcip, packet.next.dstip)
	    if n.srcip not in self.routingTable[dpid]:
            	log.debug('DPID %d: Added IP %s into routing Table, output port %d' % (dpid, str(n.srcip), inport))
            	self.routingTable[dpid][n.srcip] = inport
            else:
            	log.debug('DPID %d: IP %s  output port %d' % (dpid, str(n.srcip), inport))

            if str(n.dstip) == str(self.routerIP[dpid]):
                if isinstance(n.next, icmp):
                    log.debug("DPID %d: ICMP packet to this router" % dpid )
                    if n.next.type == pkt.TYPE_ECHO_REQUEST:
                        #Generate ICMP reply
                        self._handle_icmp_reply(dpid, packet, n.srcip, n.dstip, pkt.TYPE_ECHO_REPLY)
            elif (n.dstip in Subnet1 and self.routerIP[dpid] in Subnet2) or (n.dstip in Subnet2 and self.routerIP[dpid] in Subnet1):
                #not in the same subnet, forward to next switch
                nextHopIP = IPAddr('10.0.%d.1' % (3-dpid))
                nextHopMac = self.arpTable[dpid][nextHopIP]
                msg = of.ofp_packet_out( buffer_id=packet_in.buffer_id, in_port=inport )
                msg.actions.append(of.ofp_action_dl_addr.set_dst( nextHopMac ))
                msg.actions.append(of.ofp_action_output( port = 1 ))
                self.connections[dpid].send(msg)
                log.debug('DPID %d, packet %s to %s, different subnet, sent to port %d', dpid, str(n.srcip), str(n.dstip), 1)

		msg = of.ofp_flow_mod()
        	msg.match.dl_type = 0x800 
        	msg.match.nw_dst = n.dstip
        	msg.actions.append( of.ofp_action_dl_addr.set_dst(nextHopMac) )
        	msg.actions.append( of.ofp_action_output(port = 1) )
        	self.connections[dpid].send(msg)
            else:
                #in the same subnet
                if n.dstip not in self.routingTable[dpid] or n.dstip not in self.arpTable[dpid]:
                    if n.dstip not in self.arpWait[dpid]:
                        self.arpWait[dpid][n.dstip] = []
                    entry = (packet_in.buffer_id, inport)
                    self.arpWait[dpid][n.dstip].append(entry)
                    log.debug('DPID %d, packet %s to %s, added to arpWait, broadcast arp request' % (dpid, str(n.srcip), str(n.dstip)))
                    self._handle_arp_request(n.srcip, n.dstip, packet.src, inport, dpid)
                else:
                    msg = of.ofp_packet_out(buffer_id=packet_in.buffer_id, in_port=inport)
                    msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][n.dstip]))
                    msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][n.dstip]))
                    self.connections[dpid].send(msg)
                    log.debug('DPID %d, packet %s to %s, same subnet, sent to port %d', dpid, str(n.srcip), str(n.dstip), self.routingTable[dpid][n.dstip])

		    msg = of.ofp_flow_mod()
        	    msg.match.dl_type = 0x800 
        	    msg.match.nw_dst = n.dstip
        	    msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[dpid][n.dstip]))
        	    msg.actions.append(of.ofp_action_output(port = self.routingTable[dpid][n.dstip]))
        	    self.connections[dpid].send(msg)


        elif isinstance(n, arp):
	    if n.protosrc not in self.routingTable[dpid]:
            	log.debug('DPID %d: Added IP %s into routing Table, output port %d' % (dpid, str(n.protosrc), inport))
            	self.routingTable[dpid][n.protosrc] = inport
            else:
            	log.debug('DPID %d: IP %s output port %d' % (dpid, str(n.protosrc), inport) )
            self._handle_arp_packet(n, inport, dpid, packet_in)


            


def launch():
    """
    The program start here
    """
    core.registerNew(Router)




