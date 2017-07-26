#!/usr/bin/env python3
"""
MultiCast Library

Send/receive UDP multicast packets.
Requires that your OS kernel supports IP multicast.

Usage:
  multicast -s (sender, IPv4)
  multicast    (receivers, IPv4)

Author: Adam Compton
        @tatanus
"""

import struct
import socket
import sys
from threading import Timer

class continuousTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

class MultiCast():
    def __init__(self, port, group, ttl=1):
        self.port = port
        self.group = group
        self.ttl = ttl
        self.stopListener = False

    def send(self, uid, msg=""):
        addrinfo = socket.getaddrinfo(self.group, None)[0]

        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

        # Set Time-to-live (optional)
        ttl_bin = struct.pack('@i', self.ttl)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)

        data = uid + ":" + msg
        s.sendto((data + '\0').encode(), (addrinfo[4][0], self.port))

    def recv(self, callback):
        # Look up multicast group address in name server and find out IP version
        addrinfo = socket.getaddrinfo(self.group, None)[0]

        # Create a socket
        s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

        # Allow multiple copies of this program on one machine
        # (not strictly needed)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind it to the port
        s.bind(('', self.port))

        group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        # Join group
        if addrinfo[0] == socket.AF_INET: # IPv4
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Loop, printing any data we receive
        while True:
            if callback == None:
                return
            data, sender = s.recvfrom(1500)
            data = data.decode()
            while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
            #callback(sender, data.split(':'))
            callback.put([sender, data])


def aaa(sender, data):
    print ("sender:" + sender + "     DATA:")
    print (data)

def main():
    MYPORT = 8193
    MYGROUP = '234.233.232.231'

    m = MultiCast(MYPORT,MYGROUP,1)

    if "-s" in sys.argv[1:]:
        t = continuousTimer(5, m.send, "12345", "Hello there")
        t.start()
    else:
        m.recv(aaa)

if __name__ == '__main__':
    main()
