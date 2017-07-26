# Legion

Name: Legion

Description: Distributed computing environment that can be used for both academic and pen testing purposes.

Components:
* Nodes (can act as both server and slave)
* Mesh networking (allows for easy growth and also allows for self healing of data paths)
* Encryption (protect the traffic)
* Send Commands to 1 or more or ALL nodes to be processed
* Commands (common)
  * EXEC (exec a command)
  * PUSH (push a file from the server to other nodes)
  * PULL (pull a file from 1 or more nodes)
  * DIST (distribute a command across multiple nodes)
  * SHELL (open remote shell to target node)
  * SCAN (built in port scanner)
  * KILL (remove a node from a system
* Interactive Shell (allow for the manual interaction with a given node)
* distribute commands (if possible, distribute a command across a large set of nodes, such as password cracking, port scanning, etc…)
	
TODO:
* more complete mesh networking
* ability to download a file from a external source
* alternate connection paths..  dns/icmp/etc...
* socks5 proxy
* clean self from system
