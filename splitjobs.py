#!/usr/bin/env python3

import os

# proof of concept is take a list of IPs, validate/expand cidr (not yet implemented), and split evenly 
# send each node it's slice and issue the commmand you want (nmap in this case)
# return results to issuing node


class Split():

    def __init__(self, clist, filename):

        #pre-sliced input list which will contain the lines from filename
        self.originalList = []

        #node count from clist dict variable in legion.MeshNet.server
        self.nodeCount = len(clist)

        if self.nodeCount <= 0:
            print("ERROR: no nodes found")
            return

        #file to be split is second argument of DIST
        self.splitFile = filename

        #check ./tmp dir and make it if not found
        if not os.path.exists('./tmp/'):
            os.makedirs('./tmp/')

        #give user some indication
        print ('splitting file %s ' % str(self.splitFile))

        #open targets file, dont die on bad filenames
        try:
            self.originalList = open(self.splitFile).readlines()
        except Exception as e:
            print(e)
            return
    
        #length of split size which is input file length divided by node count
        size_of_each_list = int(len(self.originalList) / self.nodeCount) # removed +1 as calling code checks for 0 nodes

        # add 1 to size of each list to account for uneven sized originalLists
        size_of_each_list += 1

        #lists is the index length
        lists = [self.originalList[x:x+size_of_each_list] for x in range(0, len(self.originalList), size_of_each_list)]
        
        # list of created files
        self.files = list()

        # for the count of how many times the original file was split
        for i in range(0,int(len(lists))):
            #write a file to ./tmp with the list index as filename and .splitout as suffix
            f = open('./tmp/'+str(i)+'.splitout', 'w')
            f.write(''.join(lists[i]))
            f.close
            self.files.append('./tmp/'+str(i)+'.splitout')


    def getFiles(self):
        return self.files

def main():
    runSplit = Split()

if __name__ == '__main__':
    main()
