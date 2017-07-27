#!/usr/bin/env python3

import socket
import sys

class Scanner():
    @staticmethod
    def checkport(host, port):
        TIMEOUT = 0.5
        socket.setdefaulttimeout(TIMEOUT)
        sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sd.connect((host, port))
        except socket.error:
            return 'CLOSED'
        else:
            sd.close()
            return 'OPEN'

    @staticmethod
    def scan(host, ports):
        openports = []
        for port in ports:
            if not Scanner.checkport(host, port) == 'CLOSED':
                openports.append(port)
    
        return openports
