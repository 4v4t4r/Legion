#!/usr/bin/env python3
"""
Communications Library

Author: Adam Compton
        @tatanus
"""

import sys
import socket
import base64
from encryption import Encryption
from utils import Utils

class Comms():
    enc = Encryption()
    RECV_BUFFER = 4096

    # ----------------------------------------------------------------------
    # SETUP SOCKETS
    # ----------------------------------------------------------------------
    @staticmethod
    # create a new multi-listener server socket
    def create_server_socket(ip, port, listen=10):
        tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tmp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tmp_socket.bind((ip, port))
        tmp_socket.listen(listen)
        return tmp_socket

    @staticmethod
    # create a new single connect to a target ip:port
    def create_direct_socket(ip, port):
        tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tmp_socket.settimeout(2)
        try :
            tmp_socket.connect((ip, port))
            return tmp_socket
        except :
            print('Unable to connect')
            print (sys.exc_info()[0])
            return None

    @staticmethod
    def test_port(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('', port)) ## Try to open port
        except OSError as e:
            if e.errno is 98: ## Errorno 98 means address already bound
                return True
            raise e
        s.close()
        return False

    # ----------------------------------------------------------------------
    # SENDING MESSAGES
    # ----------------------------------------------------------------------
    @staticmethod
    # broadcast messages to all connected clients
    def broadcast(SOCKET_LIST, IGNORE_LIST, message):
        for sock in SOCKET_LIST:
            # do not send to self or stdio
            if sock not in IGNORE_LIST and sock != sys.stdin:
                try :
                    Comms.sendMsg(sock, message)
                except Exception as e:
                    print(e)
                    # broken socket connection
                    sock.close()
                    # broken socket, remove it
                    if sock in SOCKET_LIST:
                        SOCKET_LIST.remove(sock)
        return SOCKET_LIST

    @staticmethod
    # read X bytes of data
    def readMsg(sock, buffer_size=4096):
        txt = sock.recv(buffer_size)
        (length,data) = txt.split(b':', 1)
        length = int(length.decode())
        #print (str(length) + "   " + str(len(data)))
        if length != len(data):
            while len(data) < length:
               #print (str(length) + "   " + str(len(data)))
               data += sock.recv(buffer_size)
        #print (str(length) + "   " + str(len(data)))

        txt = Comms.decodeMsg(data)
        return txt

    @staticmethod
    def recvFile(sock, filesize,  buffer_size=4096):
        txt = b''
        size = len(txt)
        #print (str(filesize))
        filesize = int(filesize)
        while size < filesize:
            #print (str(size) + "  " + str(filesize))
            #data = sock.recv(filesize)
            data = sock.recv(buffer_size)
            if not data:
                break
            if len(data) + size > size:
                data = data[:filesize-size]
            txt += data
            size = len(txt)
        #print (str(size) + "  " + str(filesize))
        return Comms.decodeMsg(txt)

    @staticmethod
    def sendFile(sock, filename):
        #read in the file and store it contents in file_data
        file_data = ""
        if (Utils.fileExists(filename)):
            file_t = open(filename, "rb")
            file_data = file_t.read()
        
        # send the initial message specifing the filename and filesize
        msg = "PUSH:" + filename + ":" + str(Comms.encodeMsgSize(file_data.decode())) + ":" +file_data.decode()
        Comms.sendMsg(sock, msg)
        
        # Now send the filecontents them selves
        #msg = file_data.decode()
        #Comms.sendMsg(sock, msg)

    @staticmethod
    # send X bytes of data
    def sendMsg(sock, data):
        msg = Comms.encodeMsg(data)
        sock.sendall((str(len(msg)) + ":").encode() + msg)

    # ----------------------------------------------------------------------
    # DATA/MSG PROCESSING
    # ----------------------------------------------------------------------
    @staticmethod
    def encodeMsg(msg):
        tmp = msg
        #tmp = tmp.encode('unicode_escape')
        tmp = tmp.encode('ISO-8859-1')
        tmp = Comms.enc.encrypt(tmp)
        tmp = base64.b64encode(tmp)
        return tmp

    @staticmethod
    def encodeMsgSize(msg):
        tmp = msg
        #tmp = tmp.encode('unicode_escape')
        tmp = tmp.encode('ISO-8859-1')
        tmp = Comms.enc.encrypt(tmp)
        tmp = base64.b64encode(tmp)
        return len(tmp)

    @staticmethod
    def decodeMsg(msg):
        tmp = msg
        tmp = base64.b64decode(tmp)
        tmp = Comms.enc.decrypt(tmp)
        #tmp = tmp.decode('unicode_escape')
        tmp = tmp.decode('ISO-8859-1')
        return tmp
