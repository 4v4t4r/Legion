#!/usr/bin/env python3

import time
import sys
import select
import re
import getopt
import uuid
import socket
import hashlib
import random
import datetime
import os
import netifaces
import fnmatch
from comms import Comms
from multicast import MultiCast
from multicast import continuousTimer
from multiprocessing import Process, Manager
from utils import Utils
from node import Node
from splitjobs import Split
from portscan import Scanner

class Legion():
    def __init__(self, ip, port, mcastChannel="234.233.232.231", mcastPort=8193):
        # standard meta info
        self.ip = ip
        self.port = port
        self.neighbors = {}     # dict of neighbor nodes
        self.exit = None        # Node to send exit traffic to
        self.exitWeight = 0     # exit weight for calculations
        self.uid = self.genUID() # personal id
        self.nodeCount = 0

        # CLIENT specific variables
        self.outputBuf = ""
        self.proclist = {}
        self.pushedfiles = {}

        # multiprocessing stuff
        self.manager = Manager()
        self.que = self.manager.Queue()

        # multicast stuff
        self.mcast = None
        self.mcastListenerThread = None
        self.mcastProbeThread = None
        self.mcastChannel = mcastChannel
        self.mcastPort = mcastPort
        self.setupMulticaster()

        # meshnet forwarding
        self.meshPort = random.randint(40000, 65000)
        self.hashMsgs = dict()
        self.meshListener = None
        self.startMeshListener()
        self.meshServerIP = ""
        self.meshServerPort = 0

    # -----------------------------------------------------
    # Meshnet code
    # -----------------------------------------------------

    # start a meshnet listener
    def startMeshListener(self):
        # make sure we find an unused port
        while Comms.test_port(self.meshPort):
            self.meshPort = random.randint(40000, 65000)

        self.meshListener = Comms.create_server_socket("0.0.0.0", self.meshPort)

    # forward any meshnet traffic to all neighbors
    def forwardTraffic(self, srcip, srcport, dstip, dstport, msg):
        for uid in self.neighbors:
            if (self.neighbors[uid].location == "Mesh"):
                if (self.neighbors[uid].ip == dstip) and (self.neighbors[uid].port == dstport):
                    # connect and send
                    remote_sock = Comms.create_direct_socket(self.neighbors[uid].ip, self.neighbors[uid].port)
                    if (remote_sock):
                        Comms.sendMsg(remote_sock, srcip + ":" + str(srcport) + ":" + dstip + ":" + str(dstport) + ":" + msg)
                        msg = srcip + ":" + str(srcport) + ":" + dstip + ":" + str(dstport) + ":" + msg
                        remote_sock.close()
                    else:
                        print ("FAILED TO SEND")
                    return
        for uid in self.neighbors:
            if (self.neighbors[uid].location == "Mesh"):
                if not ((self.neighbors[uid].ip == srcip) and (self.neighbors[uid].port == srcport)):
                    # connect and send
                    remote_sock = Comms.create_direct_socket(self.neighbors[uid].ip, self.neighbors[uid].port)
                    if (remote_sock):
                        Comms.sendMsg(remote_sock, srcip + ":" + str(srcport) + ":" + dstip + ":" + str(dstport) + ":" + msg)
                        remote_sock.close()
                    else:
                        print ("FAILED TO SEND")
        return

    # TODO LATER
    def findExitRoute(self, ip, port):
        if self.testConnectivity(ip, port):
            self.exit = None
        else:
            best = None
            lowest = None
            #for uid, neighbor in self.neighbors:
            #    True
            #    # ask each neighbor for their exit node and weight, then pick the lowest
            #    # if weight < lowest ... lowest = weight ... best = uid
            if best:
                self.exit = best
                self.exitWeight = lowest

    # -----------------------------------------------------
    # Multicast Code
    # -----------------------------------------------------

    # setup multicaster configuration
    def setupMulticaster(self):
        if (self.mcastChannel and self.mcastPort):
            self.mcast = MultiCast(self.mcastPort, self.mcastChannel, 1)
            # setup listener
            self.mcastListenerThread = Process(target=self.mcast.recv, args=(self.que,))
            self.mcastListenerThread.start()

    # used for generating unique self id
    def genUID(self):
        return str(uuid.uuid1())

    # send out multicast probe 
    def probeNeighbors(self):
        if (self.mcast):
            self.mcastProbeThread = continuousTimer(1, self.mcast.send, self.uid, str(self.meshPort))

    # test to see if we can connect to a neighbor/node
    def testConnection(self, neighbor):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((neighbor.ip,neighbor.port))
        if result == 0:
            return True
        else:
            return False

    # test to see if we can still communicate to our neighbors
    def testNeighbors(self):
        for uid in self.neighbors:
            if not self.testConnection(self.neighbors[uid].ip, self.neighbors[uid].port):
                self.rmNeighbor(uid)

    def isNeighbor(self, uid):
        for key in self.neighbors:
            if uid == self.neighbors[key].uid:
                return True
        return False

    # add a new neighbor
    def addNeighbor(self):
        while not self.que.empty():
            t = self.que.get()
            ip = str(t[0][0])
            data = t[1].split(':')
            uid = str(data[0][1:])
            port = int(data[1])
            temp = Node(ip, port, uid, 1, None, "Mesh")
            if (not self.isNeighbor(uid)):
                print ("\nFound Neighbor...........")
                self.neighbors[self.nodeCount] = temp
                self.nodeCount+= 1
            else:
                None

    # delete a neighbor we can no longer access
    def rmNeighbor(self, uid):
        del self.neighbors[uid]

    # return a list of neighbor nodes
    def listNeighbors(self):
        n_list = []
        for uid in self.neighbors:
            tmp_str = str(uid) + "::" + self.neighbors[uid].ip + ":"  + str(self.neighbors[uid].port)
            n_list.append(tmp_str)
        return n_list

    # -----------------------------------------------------
    # Client/Server code
    # -----------------------------------------------------

    def client_process_cmds(self, msg, sock):
        if (msg.startswith("EXIT")):
            sys.stdout.write("Client Terminated!!!\r\n")
            self.cleanup()
        elif (msg.startswith("SCAN")):
            p = re.compile("SCAN:(.+?):(.+?):(.+)")
            m = p.match(msg)
            if (m):
                print("Scanning: " + m.group(1) + "  " + m.group(2) + "-" + m.group(3))
                self.outputBuf += '\r\n'.join(str(x) for x in Scanner.scan(m.group(1), range(int(m.group(2)), int(m.group(3)))))
                print ("finished")
                print (self.outputBuf)
        elif (msg.startswith("WGET")):
            p = re.compile("WGET\s+(.+)")
            m = p.match(msg)
            if (m):
                print("Getting: " + m.group(1))
                Utils.wget(m.group(1))
        elif (msg.startswith("EXEC")):
            p = re.compile("EXEC\s+(.+)")
            m = p.match(msg)
            if (m):
                sys.stdout.write("Executing [%s]\n" % m.group(1))
        
                self.outputBuf += "\n\n" + Utils.execWait(m.group(1)).decode('unicode_escape')

                #pid = Utils.exec(m.group(1))
                #self.proclist[pid] = m.group(1)
            else:
                None
        elif (msg.startswith("PROCLIST")):
            for pid in self.proclist:
                self.outputBuf += str(pid) + "    " + self.proclist[pid] + '\n'
        elif (msg.startswith("EXIST")):
            (tmp, cmd) = msg.split(':', 1)
            result = "false"
            (short_cmd, args) = cmd.split(' ')
            if (Utils.which(short_cmd)):
                result = "true"
            Comms.sendMsg(sock, result)
        elif (msg.startswith("CLEARBUFFER")):
            self.outputBuf = ""
        elif (msg.startswith("GETBUFFER")):
            created_sock = False
            if not sock:
                # assume we are returning something to the mesh server
                sock = Comms.create_direct_socket(self.meshServerIP, int(self.meshServerPort))
                created_sock = True
                self.outputBuf = self.ip + ":" + str(self.meshPort) + ":" + self.meshServerIP + ":" + str(self.meshServerPort) + ":" +self.outputBuf

            Comms.sendMsg(sock, self.outputBuf)

            if created_sock:
                sock.close()
        elif (msg.startswith("PUSH")):
            (tmp, filename, file_len, file_data) = msg.split(':', 3)
            filename = os.path.basename(filename)
            print("received file: " + filename)
            filename_orig = filename
            filename = "tmp/" + filename
            if (Utils.fileExists(filename)):
                filename += "_" + Utils.getRandStr(5)
            self.pushedfiles[filename_orig] = filename
            Utils.writeFile(file_data, filename, "ab")
        elif (msg.startswith("PULL")):
            (tmp, filename) = msg.split(':', 1)
            file_data = ""
            if (Utils.fileExists(filename)):
                file_t = open(filename, "rb") 
                file_data = file_t.read()
            self.outputBuf = file_data.decode()
        elif (msg.startswith("NEIGHBORS")):
            self.outputBuf = '\n'.join(self.listNeighbors())
        else:
            sys.stdout.write(msg)

    def client(self, host, port):
        slist = [] #array of client sockets

        # start the multicast probes
        self.probeNeighbors()
        
        if (host and port):
            remote_server_sock = Comms.create_direct_socket(host, port)
            slist.append(remote_server_sock)

        # add mesh listener if necessary
        if (self.meshListener):
            slist.append(self.meshListener)
            print ("MeshNet Listener started on port: " + str(self.meshPort))

        while(1):
            self.addNeighbor()
            # get the list sockets which are ready to be read through select
            # 4th arg, time_out  = 0 : poll and never block
            ready_to_read,ready_to_write,in_error = select.select(slist,[],[],0)
        
            for sock in ready_to_read:
                if (self.meshListener) and (sock == self.meshListener):
                    sockfd, addr = sock.accept()
                    msg = Comms.readMsg(sockfd, 4096)

                    # construct msg hash
                    m = hashlib.sha256()
                    m.update(msg.encode('ISO-8859-1'))
                    hash_key = m.hexdigest()
                    timestamp = datetime.datetime.now()

                    good = True
                    if hash_key in self.hashMsgs:
                        stored_timestamp = datetime.datetime.strptime(self.hashMsgs[hash_key], '%Y-%m-%d %H:%M:%S.%f')
                        if (timestamp <= (stored_timestamp + datetime.timedelta(minutes = 10))):
                            good = False

                    # if we have not seen the message before then process it
                    if good:
                        self.hashMsgs[hash_key] = str(timestamp)
                        (srcip, srcport, dstip, dstport, data) = msg.split(':', 4)
                        
                        # set mesh server ip:port
                        self.meshServerIP = srcip
                        self.meshServerPort = int(srcport)

                        if (dstip == self.ip) and (int(dstport) == self.meshPort):
                            #process msg
                            self.client_process_cmds(data, None) 
                        else:
                            self.forwardTraffic(srcip, srcport, dstip, dstport, data)
                elif (sock == remote_server_sock): # a new connection request received
                    msg = Comms.readMsg(sock, 4096)
                    msg = msg.lstrip('\r\n')
                    self.client_process_cmds(msg, sock) 
    
   
    def rmtsh(self, tmp_sock, slist, server_sock):
        prompt = "rmtsh (EXIT to quit) "
        cwd = "" # used to keep track of current working dir
        # attempt to get the pwd/cwd so we can use in in our commands
        Comms.sendMsg(tmp_sock, "EXEC pwd") 
        Comms.sendMsg(tmp_sock, "GETBUFFER")
    
        while (1):
            displayPrompt = False
            ready_to_read,ready_to_write,in_error = select.select(slist,[],[],0)
    
            for sock in ready_to_read:
                displayPrompt = False
                if (sock == sys.stdin): # server sending message
                    msg = sys.stdin.readline()
                    msg = msg.lstrip('\r\n ') # clean up line removing any starting spaces and CRLF
                    if 'EXIT' in msg: # did we enter EXIT?
                        return
                    else: #must have entered some other command
                        msg = msg.rstrip('\r\n')
                        if len(msg) > 0: # is this a blank line?   just a return?
                            if (cwd): # do we have a stored cwd?
                                msg = "cd " + cwd + " ; " + msg  # if so, change command to prepend a   "cd <cwd> ; " 
                            Comms.sendMsg(tmp_sock, "EXEC " + msg + " ; pwd")  # append a "; pwd" to the command so we can find out the ending working directory
                            Comms.sendMsg(tmp_sock, "GETBUFFER")
                        else:
                            displayPrompt = True
                elif (sock != server_sock) and (sock != sys.stdin):
                    msg = Comms.readMsg(sock, 4096)
                    msg = msg.rstrip('\r\n')
                    indx = msg.rfind('\n') # what is the ending line break?
                    if indx == -1:
                        indx = 0
                    cwd = msg[indx:].lstrip('\r\n').rstrip('\r\n')
                    msg = msg[:indx]
                    sys.stdout.write("\r\n")
                    sys.stdout.write(msg)
                    sys.stdout.write("\r\n")
                    displayPrompt = True
                else:
                    displayPrompt = False
            if (displayPrompt):
                sys.stdout.write(prompt + cwd + "> ")
                sys.stdout.flush()
  
    def server_process_cmds(self, slist, ignore_list, msg, server_sock):
        displayPrompt = False

        if (msg.startswith("NODE:")):
            p = re.compile("NODE:(\d+)\s+(.*)")
            m = p.match(msg)
            if (m):
                if (self.neighbors[int(m.group(1))].location == "Direct"):
                    displayPrompt = self.server_process_cmds([self.neighbors[int(m.group(1))].socket], ignore_list, m.group(2), server_sock)
                else:
                    sys.stdout.write("Can only use NODE on Direct connections" + '\r\n')
                    displayPrompt = True
            else:
                displayPrompt = True
        elif (msg.startswith("HELP") or msg.startswith("help") or msg.startswith("?") or msg.startswith("/?")):
            sys.stdout.write(getHelp())
            displayPrompt = True
        elif (msg.startswith("LIST")):
            sys.stdout.write("List of current client/slave nodes:\r\n")
            sys.stdout.write("------------------------------------------------------\r\n")
            sys.stdout.write('{:5} {:21} {:13}'.format("<#>", "<IP>:<PORT>", "<Direct/Mesh>"))
            sys.stdout.write("\r\n")
            for uid in self.neighbors:
                sys.stdout.write('{:5} {:21} {:13}'.format(str(uid), self.neighbors[uid].ip + ":" + str(self.neighbors[uid].port), self.neighbors[uid].location))
                sys.stdout.write("\r\n")
            displayPrompt = True
        elif (msg.startswith("PUSH")):
            (tmp, filename) = msg.split(':', 1)
            for key in self.neighbors:
                if (self.neighbors[key].location == "Direct"):
                    if self.neighbors[key].socket in slist:
                        Comms.sendFile(self.neighbors[key].socket, filename)
            displayPrompt = True
        elif (msg.startswith("PULL")):
            p = re.compile("PULL:(.*)")
            m = p.match(msg)
            if (m):
                Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("SCAN")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("WGET")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("EXEC")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("SHELL")):
            p = re.compile("SHELL:(\d+)")
            m = p.match(msg)
            if (m):
                if (self.neighbors[int(m.group(1))].location == "Direct"):
                    self.rmtsh(self.neighbors[int(m.group(1))].socket, slist, server_sock)
                else:
                    sys.stdout.write("Can only use SHELL on Direct connections" + '\r\n')
            displayPrompt = True
        elif (msg.startswith("CLEARBUFFER")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True 
        elif (msg.startswith("GETBUFFER")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = False
        elif (msg.startswith("EXIT")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True 
        elif (msg.startswith("QUIT")):
            self.cleanup()
        elif (msg.startswith("PROCLIST")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("NEIGHBORS")):
            Comms.broadcast(slist, ignore_list, msg)
            displayPrompt = True
        elif (msg.startswith("MESH:")):
            p = re.compile("MESH:(\d+)\s+(.*)")
            m = p.match(msg)
            if (m):
                if (self.neighbors[int(m.group(1))].location == "Mesh"):
                    n = self.neighbors[int(m.group(1))]
                    self.forwardTraffic(self.ip, self.meshPort, n.ip, n.port, m.group(2))
            displayPrompt = True
        elif (msg.startswith("DIST")):
            #match DIST <command> <file>
            #\s+(.+) for command
            #(.*)for filename
            #p compiles the regex
            p = re.compile("DIST:(.*?) (.*)")
            #m matches DIST <something> <something>.
            m = p.match(msg)

            #m.group(1) is the command, m.group(2) is the filename
            
            #correct command matches? then lets go!
            if (m):
                # make a local list to use
                clist = dict()
                # only copy the Direct neighbors into the new list
                count = 0
                for key in self.neighbors:
                    if self.neighbors[key].location == "Direct":
                        print ("testing if command exists : ")
                        Comms.sendMsg(self.neighbors[key].socket, "EXIST:" + m.group(2))
                        if Comms.readMsg(self.neighbors[key].socket) == "true":
                            clist[count] = self.neighbors[key]
                            print ('clist '+clist[count].ip)
                            count += 1

                #check for clients, sending commands is pointless if no clients
                if len(clist) < 1:
                    #is this the best way? probably not
                    print('no clients!')
                    #give the user back their prompt
                    displayPrompt = True

                #ok, we have clients...now what?
                else:
                    #first, split the input file into n parts, where n is count of nodes
                    #splitjobs.Split takes clist to count nodes, and the filename to split
                    #splitjobs.Split will then write files to ./tmp called 0.splitout 1.splitout ,etc
                    s = Split(clist, m.group(1))
                    files = s.getFiles()

                    print(files)

                    #command logic check--todo
                    #if m.group(2) is nmap, then xx, if its hashcat, then... etc
                    #for now assume any command we want to distribute accepts a text file

                    #for each client in clist
                    for i in range (0,len(clist)):
                        filename = files.pop()
                        for key in self.neighbors:
                            if self.neighbors[key].uid == clist[i].uid:
                                #send this file to a node. file 0.splitout would go to node 0
                                #PUSH code goes here to transfer 0.splitout to node 1 (0th node), etc

                                #issue PUSH as a server command
                                print("running NODE:" + str(key) + " PUSH:tmp/"+filename)
                                displayPrompt = self.server_process_cmds([clist[i].socket], ignore_list, "NODE:%s PUSH:%s" % (key,filename), server_sock)

                                time.sleep(2)
                        
                                print("running NODE:%s %s " % (i,m.group(2))+filename)
                                displayPrompt = self.server_process_cmds([clist[i].socket], ignore_list, "NODE:%s EXEC %s" % (key,m.group(2))+''+filename, server_sock)

                                time.sleep(2)
                                break
        else:                       
            # do nothing for now
            displayPrompt = True

        return displayPrompt

    def server(self, host, port):
        slist = [] #array of client sockets
        nid = 0
        prompt = "# (stuck? type HELP)> "
    
        server_sock = Comms.create_server_socket(host, port)
        slist.append(server_sock)
        slist.append(sys.stdin)
    
        print ("Server started on IPs : " + str(host))
        print ("Server started on port: " + str(port))

        # add mesh listener if necessary
        if (self.meshListener):
            slist.append(self.meshListener)
            print ("MeshNet Listener started on port: " + str(self.meshPort))
    
        sys.stdout.write(prompt)
        sys.stdout.flush()
    
        displayPrompt = False
    
        while(1):
            self.addNeighbor()
            displayPrompt = False
            # get the list sockets which are ready to be read through select
            # 4th arg, time_out  = 0 : poll and never block
            ready_to_read,ready_to_write,in_error = select.select(slist,[],[],0)

            for sock in ready_to_read:
                displayPrompt = False
                if (self.meshListener) and (sock == self.meshListener):
                    sockfd, addr = sock.accept()
                    msg = Comms.readMsg(sockfd, 4096)

                    # construct msg hash
                    m = hashlib.sha256()
                    m.update(msg.encode('ISO-8859-1'))
                    hash_key = m.hexdigest()
                    timestamp = datetime.datetime.now()

                    good = True
                    if hash_key in self.hashMsgs:
                        stored_timestamp = datetime.datetime.strptime(self.hashMsgs[hash_key], '%Y-%m-%d %H:%M:%S.%f')
                        if (timestamp >= (stored_timestamp + datetime.timedelta(minutes = 10))):
                            good = False

                    # if we have not seen the message before then process it
                    if good:
                        self.hashMsgs[hash_key] = timestamp
                        (srcip, srcport, dstip, dstport, data) = msg.split(':', 4)
                        if (dstip == self.ip) and (int(dstport) == self.meshPort):
                            #process msg
                            sys.stdout.write(data)
                            sys.stdout.write("\r\n")
                            displayPrompt = True
                        else:
                            # the server does not forward messages
                            None
                elif (sock == server_sock): # a new connection request received
                    nid = nid+1
                    sockfd, addr = sock.accept()
                    slist.append(sockfd)
                    self.neighbors[self.nodeCount] = Node(addr[0], addr[1], self.genUID(), 1, sockfd, "Direct")
                    self.nodeCount += 1
                    sys.stdout.write("\r" + "Client %i : (%s, %s) connected\n" % (nid, addr[0], addr[1]))
                    displayPrompt = True
                elif (sock == sys.stdin): # server sending message
                    msg = sys.stdin.readline()
                    msg = msg.lstrip('\r\n')
                    msg = msg.rstrip('\r\n')

                    displayPrompt = self.server_process_cmds(slist, [server_sock, self.meshListener], msg, server_sock)
    
                elif (sock != server_sock) and (sock != sys.stdin):
                    msg = Comms.readMsg(sock, 4096)
                    sys.stdout.write("=====================")
                    sys.stdout.write("\r\n")
                    (ip, port) = sock.getpeername()
                    sys.stdout.write(ip + ":" + str(port))
                    sys.stdout.write("\r\n")
                    sys.stdout.write("---------------------")
                    sys.stdout.write("\r\n")
                    sys.stdout.write(msg)
                    sys.stdout.write("\r\n")
                    displayPrompt = True
                else:
                    sys.stdout.write("[UNKNOWN SOCKET]")
                    sys.stdout.write("\r\n")
                    displayPrompt = True
    
            if (displayPrompt):
                sys.stdout.write(prompt)
                sys.stdout.flush()

    # ----------------------------
    # CTRL-C display and exit
    # ----------------------------
    def ctrlc(self):
        print("Ctrl-C caught!!!")
        self.cleanup()

    def cleanup(self):
        try:
            if self.meshListener:
                self.meshListener.close()
            if self.mcastProbeThread:
                self.mcastProbeThread.stop()
            if self.mcastListenerThread:
                self.mcastListenerThread.terminate()
        except: # bad form, but just a general catch all for now
            None
        sys.exit(0)

def getLocalIP():
    default_iface = netifaces.gateways()['default'][netifaces.AF_INET][1]
    default_data = netifaces.ifaddresses(default_iface).setdefault(netifaces.AF_INET, [{'addr':'No IP addr'}])
    for i in default_data:
        return (i['addr'])

def selectLocalIP():
    ips = list() 
    print ("------------------------")
    i = 1
    for ifaceName in netifaces.interfaces():
        tmp_ips = [i['addr'] for i in netifaces.ifaddresses(ifaceName).setdefault(netifaces.AF_INET, [{'addr':'No IP addr'}] )]
        ips += tmp_ips
        print(str(i) + ": " + str(tmp_ips) + "    (" + ifaceName +")")
        i = i + 1
    print ("------------------------")
    print ("")
    answer = input("Which IP to use as Server IP? ")

    return ips[int(answer)-1]

def getHelp():
    tmp = "HELP = List of Available Commands\r\n"
    tmp += "---------------------------------------------------------------------\r\n"
    tmp += "HELP                          displays this message\r\n"
    tmp += "LIST                          displays a list of all nodes\r\n"
    tmp += "EXEC                          executes a command on all nodes\r\n"
    tmp += "DIST:<file to split> <cmd>    distributes a job on all nodes and returns data\r\n"
    tmp += "GETBUFFER                     pulls any output from a node\r\n"
    tmp += "CLEARBUFFER                   clears any buffered output from a node\r\n"
    tmp += "PUSH:<filename>               push a file to remote node(s)\r\n"
    tmp += "PULL:<filename>               pull a file from remote node(s)\r\n"
    tmp += "NEIGHBORS                     displays a list of all neighbor nodes\r\n"
    tmp += "SHELL:#                       opens remote shell on client #\r\n"
    tmp += "NODE:# <cmd>                  issues another command only to node #\r\n"
    tmp += "MESH:# <cmd>                  send message/cmd to remote node\r\n"
    tmp += "SCAN:<ip>:<start port>:<stop port>    perform port scan\r\n"
    tmp += "WGET <url>                    download file from URL\r\n"
    tmp += "EXIT                          shut down the nodes\r\n"
    tmp += "QUIT                          EXITS server\r\n"
    tmp += "\r\n"
    return tmp

def usage():
    print('python3 legion.py -i <server ip> -p <server port>')
    print('     -i, --serverip=       ip of the server node (not used in when -s is set)')
    print('     -p, --serverport=     port the server node is listening on')
    print('     -s                    run in server mode')
    print('     -h                    help (this message)')

if __name__ == "__main__":

    n_ip = getLocalIP()
    n_port = None
    s_ip = None
    s_port = None
    s_flag = False

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hsi:p:",["serverip=","serverport="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-i", "--serverip"):
            s_ip = arg
        elif opt in ("-p", "--serverport"):
            s_port = int(arg)
        elif opt in ("-s"):
            s_flag = True

    mnet = Legion(n_ip, n_port)
    try:
        if (s_flag):
            if not s_ip:
                #s_ip = "0.0.0.0"
                s_ip = selectLocalIP()
            sys.exit(mnet.server(s_ip, s_port))
        else:
            sys.exit(mnet.client(s_ip, s_port))
    except KeyboardInterrupt:
        mnet.ctrlc()
    except:
        sys.exit(0)
