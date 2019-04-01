EE 555 Project
Wenhan Tang 1210637460
Chenguang He 8977866134

Folder part_2 contains 2 other files:
advance_router.py - this file is the controller of the router.
part2_topo.py - this file is the topology for router.

To Run:
%advance_router.py:
%open two terminals
%in the first terminal
%copy advance_router.py to ~/pox/pox/misc
./pox.py log.level --DEBUG misc.advance_router misc.full_payload  
%in the second terminal 
%copy part2_topo.py to root 
sudo mn -c
sudo mn --custom part2_topo.py --topo Part2_Topo --mac --controller=remote,ip=127.0.0.1
pingall 

advance_router.py used reference from https://github.com/zhan849/ee555/blob/master/part2/router_part2.py