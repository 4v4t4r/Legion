#!/usr/bin/env python3
"""
Encryption Library

Author: Adam Compton
        @tatanus
"""

import hashlib
from Crypto.Cipher import AES

class Encryption():
    def __init__(self, key="ShouldChangeThis"):
        self.key = hashlib.sha256(key.encode()).digest()
        self.iv = "gzQCdoBEJugBFhm9".encode()

    def getKey(self):
        return self.key

    def encrypt(self, plaintext):
        aes = AES.new(self.key, AES.MODE_CFB, self.iv)
        return aes.encrypt(plaintext)

    def decrypt(self, ciphertext):
        aes = AES.new(self.key, AES.MODE_CFB, self.iv)
        return aes.decrypt(ciphertext)

def main():
    enc = Encryption("1234123412341234")
    #enc = Encryption("12341234123412341234123412341234")
    #enc = Encryption("1234123412341234ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    plaintext = "Testing 123"
    ciphertext = enc.encrypt(plaintext)
    print (plaintext)
    print (ciphertext)
    print (enc.decrypt(ciphertext))
    print (enc.getKey())

if __name__ == '__main__':
    main()
