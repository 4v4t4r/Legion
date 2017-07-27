# Legion

Name: Legion

Description: Distributed computing environment that can be used for both academic and pen testing purposes.

Components:
* Nodes (can act as both server and slave)
* Mesh networking (allows for easy growth and also allows for self healing of data paths)
* Encryption (protect the traffic)
* Send Commands to 1 or more or ALL nodes to be processed
* Commands (common)
  * HELP (displays this message)
  * LIST (displays a list of all nodes)
  * EXEC (executes a command on all nodes)
  * DIST:<file to split> <cmd> (distributes a job on all nodes and returns data)
  * GETBUFFER (pulls any output from a node)
  * CLEARBUFFER (clears any buffered output from a node)
  * PUSH:<filename> (push a file to remote node(s))
  * PULL:<filename> (pull a file from remote node(s))
  * NEIGHBORS (displays a list of all neighbor nodes)
  * SHELL:# (opens remote shell on client #)
  * NODE:# <cmd> (issues another command only to node #)
  * MESH:# <cmd> (send message/cmd to remote node)
  * SCAN:<ip>:<start port>:<stop port> (perform port scan)
  * WGET <url> (download file from URL)
  * EXIT (shut down the nodes)
  * QUIT (EXITS server)
* Interactive Shell (allow for the manual interaction with a given node)
* distribute commands (if possible, distribute a command across a large set of nodes, such as password cracking, port scanning, etc…)
	
TODO:
* more complete mesh networking
* alternate connection paths..  dns/icmp/etc...
* socks5 proxy
* clean self from system
