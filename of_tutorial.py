#copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This component is for use with the OpenFlow tutorial.
It acts as a simple hub, but can be modified to act like an L2
learning switch.
It's roughly similar to the one Brandon Heller did for NOX.

EE 555 Project
Wenhan Tang 1210637460
Chenguang He 8977866134
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()



class Tutorial (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

    # Use this table to keep track of which ethernet address is on
    # which switch port (keys are MACs, values are ports).
    self.mac_to_port = {}
    self.dpid = connection.dpid
    self.flow = {}


  def resend_packet (self, packet_in, out_port):
    """
    Instructs the switch to resend a packet that it had sent to us.
    "packet_in" is the ofp_packet_in object the switch had sent to the
    controller due to a table-miss.
    """
    msg = of.ofp_packet_out()
    msg.data = packet_in

    # Add an action to send to the specified port
    action = of.ofp_action_output(port = out_port)
    msg.actions.append(action)

    # Send message to switch
    self.connection.send(msg)


  def act_like_hub (self, packet, packet_in):
    """
    Implement hub-like behavior -- send all packets to all ports besides
    the input port.
    """

    # We want to output to all ports -- we do that using the special
    # OFPP_ALL port as the output port.  (We could have also used
    # OFPP_FLOOD.)
    self.resend_packet(packet_in, of.OFPP_ALL)

    # Note that if we didn't get a valid buffer_id, a slightly better
    # implementation would check that we got the full data before
    # sending it (len(packet_in.data) should be == packet_in.total_len)).


  def act_like_switch (self, packet, packet_in):
    #learn the port for the source mAC
    self.mac_to_port[packet.src] = packet_in.in_port
    log.debug('Switch(dpid) %d learns port %d as source port' % (self.dpid, self.mac_to_port[packet.src]))

    #condition if the port associated with the destination MAC of the packet is known
    if packet.dst in self.mac_to_port:
	outport = self.mac_to_port.get(packet.dst)
	if (outport != None):
        	self.resend_packet(packet_in, self.mac_to_port[packet.dst]) #send the packet out the associated port
		log.debug('Switch(dpid) %d is sending packet to port %d' % (self.dpid, self.mac_to_port[packet.dst]))
		if packet.dst not in self.flow: #condition if not in flow table
        		msg = of.ofp_flow_mod()
			msg.match = of.ofp_match.from_packet(packet)
        		msg.actions.append(of.ofp_action_output(port = self.mac_to_port[packet.dst])) #push to flow table
			self.connection.send(msg)
			self.flow[packet.dst] = self.mac_to_port[packet.dst]
        		log.debug('Switch(dpid) %d is adding flow to the table, dst ip %s & port %d' % (self.dpid, packet.dst, self.mac_to_port[packet.dst]))
    else:
        self.resend_packet(packet_in, of.OFPP_ALL)
	log.debug('Switch(dpid) %d is trying to boardcast' % self.dpid) #broadcast

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """

    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.

    # Comment out the following line and uncomment the one after
    # when starting the exercise.
    #self.act_like_hub(packet, packet_in)
    log.debug('Switch(dpid) %d is trying to send packet from %s to %s' % (self.dpid, packet.src, packet.dst))
    self.act_like_switch(packet, packet_in)



def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Tutorial(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
