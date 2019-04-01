EE 555 Project
Wenhan Tang 1210637460
Chenguang He 8977866134

Folder bonus contains 2 other files:
bonus_router.py - this file is the controller for router.
bonus_topo.py - this file is the topology for router.

To Run:
%bonus_router.py:
%open two terminals
%in the first terminal
%copy bonus_router.py to ~/pox/pox/misc
./pox.py log.level --DEBUG misc.bonus_router misc.full_payload  
%in the second terminal
%copy bonus_topo.py to root 
sudo mn -c
sudo mn --custom bonus_topo.py --topo Bonus_Topo --mac --controller=remote,ip=127.0.0.1
pingall 
