#!/usr/bin/env python3

#
# Generic class for any nodes
#
class Node():
    def __init__(self, ip="", port=-1, uid=None, hops=1, socket=None, location="Direct"):
        self.ip = ip
        self.port = port
        self.uid = uid
        self.os = ""
        self.hops = hops
        self.socket = socket
        self.location = location

    @property
    def ip(self):
        return self.__ip

    @property
    def port(self):
        return self.__port

    @property
    def uid(self):
        return self.__uid

    @property
    def hops(self):
        return self.__hops

    @property
    def socket(self):
        return self.__socket

    @property
    def location(self):
        return self.__location

    @ip.setter
    def ip(self, ip):
        self.__ip = ip

    @port.setter
    def port(self, port):
        self.__port = port

    @uid.setter
    def uid(self, uid):
        self.__uid = uid

    @hops.setter
    def hops(self, hops):
        self.__hops = hops

    @socket.setter
    def socket(self, socket):
        self.__socket = socket

    @location.setter
    def location(self, location):
        self.__location = location
