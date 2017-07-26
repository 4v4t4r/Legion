#!/usr/bin/env python3
"""
Common Utils

Author: Adam Compton
        @tatanus
"""

import threading 
import configparser
import fcntl
import os
import random
import socket
import string
import struct
import subprocess
import sys
import time

class Utils():
    @staticmethod
    def newLine():
        return os.linesep

    @staticmethod
    def isWriteable(filename):
        try:
            fp = open(filename, 'a')
            fp.close()
            return True
        except IOError:
            return False

    @staticmethod
    def isReadable(filename):
        try:
            fp = open(filename, 'r')
            fp.close()
            return True
        except IOError:
            return False

    @staticmethod
    def isExecutable(filename):
        return Utils.fileExists(filename) and os.access(filename, os.X_OK)

    @staticmethod
    def which(program):
        import os
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    
        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
    
        return None

    @staticmethod
    def fileExists(filename):
        filename = os.path.abspath(filename)
        aaa = os.path.isfile(filename)
        return os.path.isfile(filename)

    @staticmethod
    def writeFile(text, filename, flag="a"):
        if text:
            fullfilename = os.path.abspath(filename)
            if not os.path.exists(os.path.dirname(fullfilename)):
                os.makedirs(os.path.dirname(fullfilename))
            fp = open(fullfilename, flag)
            fp.write(str.encode(text))
            fp.close()

    @staticmethod
    def validateExecutable(name):
        path = None
        # yes I know this is an obvious command injection...
        # but we trust the users correct?  ;)
        tmp = Utils.execWait("which " + name).strip()
        if (tmp) and (tmp != "") and Utils.isExecutable(tmp):
            path = tmp
        return path

    @staticmethod
    def getRandStr(length):
        return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

    @staticmethod
    def loadConfig(filename):
        config = {}
        if Utils.isReadable(filename):
            parser = configparser.SafeConfigParser()
            parser.read(filename)
            for section_name in parser.sections():
                for name, value in parser.items(section_name):
                    config[name] = value
        return config

    @staticmethod
    def uniqueList(old_list):
        new_list = []
        if old_list != []:
            for x in old_list:
                if x not in new_list:
                    new_list.append(x)
        return new_list

    @staticmethod
    def exec(cmd):
        return subprocess.Popen(cmd).pid

    @staticmethod
    def execWait(cmd, outfile=None, timeout=0):
        result = ""
        env = os.environ
        proc = subprocess.Popen(cmd, executable='/bin/bash', env=env, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)

        if timeout:
            timer = threading.Timer(timeout, proc.kill)
            timer.start()
        result = proc.communicate()[0]
        if timeout:
            if timer.is_alive():
                timer.cancel()
        if outfile:
            if Utils.fileExists(outfile):
                print("FILE ALREADY EXISTS!!!!")
            else:
                tmp_result = "\033[0;33m(" + time.strftime(
                    "%Y.%m.%d-%H.%M.%S") + ") <pentest> #\033[0m " + cmd + Utils.newLine() + Utils.newLine() + result
                Utils.writeFile(tmp_result, outfile)
        return result

class Colors(object):
    N = '\033[m'  # native
    R = '\033[31m'  # red
    G = '\033[32m'  # green
    O = '\033[33m'  # orange
    B = '\033[34m'  # blue


class ProgressBar():
    def __init__(self, end=100, width=10, title="", display=None):
        self.end = end
        self.width = width
        self.title = title
        self.display = display
        self.progress = float(0)
        self.bar_format = '[%(fill)s>%(blank)s] %(progress)s%% - %(title)s'
        self.rotate_format = '[Processing: %(mark)s] %(title)s'
        self.markers = '|/-\\'
        self.curmark = -1
        self.completed = False
        self.reset()

    def reset(self, end=None, width=None, title=""):
        self.progress = float(0)
        self.completed = False
        if (end):
            self.end = end
        if (width):
            self.width = width
        self.curmark = -1
        self.title = title

    def inc(self, num=1):
        if (not self.completed):
            self.progress += num

            cur_width = (self.progress / self.end) * self.width
            fill = int(cur_width) * "-"
            blank = (self.width - int(cur_width)) * " "
            percentage = int((self.progress / self.end) * 100)

            if (self.display):
                self.display.verbose(
                    self.bar_format % {'title': self.title, 'fill': fill, 'blank': blank, 'progress': percentage},
                    rewrite=True, end="", flush=True)
            else:
                sys.stdout.write('\r' + self.bar_format % {'title': self.title, 'fill': fill, 'blank': blank,
                                                           'progress': percentage})
                sys.stdout.flush()

            if (self.progress == self.end):
                self.done()
        return self.completed

    def done(self):
        self.completed = True

    def rotate(self):
        if (not self.completed):
            self.curmark = (self.curmark + 1) % len(self.markers)
            if (self.display):
                self.display.verbose(self.rotate_format % {'title': self.title, 'mark': self.markers[self.curmark]},
                                     rewrite=True, end="", flush=True)
            else:
                sys.stdout.write('\r' + self.rotate_format % {'title': self.title, 'mark': self.markers[self.curmark]})
                sys.stdout.flush()
        return self.completed


class Display():
    def __init__(self, verbose=False, debug=False, logpath=None):
        self.VERBOSE = verbose
        self.DEBUG = debug
        self.logpath = logpath
        self.ruler = '-'

    def setLogPath(self, logpath):
        self.logpath = logpath

    def enableVerbose(self):
        self.VERBOSE = True

    def enableDebug(self):
        self.DEBUG = True

    def log(self, s, filename="processlog.txt"):
        if (self.logpath is not None):
            fullfilename = self.logpath + filename
            if not os.path.exists(os.path.dirname(fullfilename)):
                os.makedirs(os.path.dirname(fullfilename))
            fp = open(fullfilename, "a")
            if (filename == "processlog.txt"):
                fp.write(time.strftime("%Y.%m.%d-%H.%M.%S") + " - " + s + "\n")
            else:
                fp.write(s)
            fp.close()

    def _display(self, line, end="\n", flush=True, rewrite=False):
        if (rewrite):
            line = '\r' + line
        sys.stdout.write(line + end)
        if (flush):
            sys.stdout.flush()
        self.log(line)

    def error(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents errors.'''
        line = line[:1].upper() + line[1:]
        s = '%s[!] %s%s' % (Colors.R, line, Colors.N)
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def output(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents normal output.'''
        s = '%s[*]%s %s' % (Colors.B, Colors.N, line)
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def alert(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents important output.'''
        s = '%s[*] %s%s' % (Colors.O, line, Colors.N)
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def verbose(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents output if in verbose mode.'''
        if self.VERBOSE:
            self.output("[VERBOSE] " + line, end=end, flush=True, rewrite=rewrite)

    def debug(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents output if in debug mode (very verbose).'''
        if self.DEBUG:
            self.output("[DEBUG]   " + line, end=end, flush=True, rewrite=rewrite)

    def yn(self, line, default=None):
        valid = {"yes": True, "y": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif (default.lower() == "yes") or (default.lower() == "y"):
            prompt = " [Y/n] "
        elif (default.lower() == "no") or (default.lower() == "n"):
            prompt = " [y/N] "
        else:
            self.alert("ERROR: Please provide a valid default value: no, n, yes, y, or None")

        while True:
            choice = self.input(line + prompt)
            if default is not None and choice == '':
                return valid[default.lower()]
            elif choice.lower() in valid:
                return valid[choice.lower()]
            else:
                self.alert("Please respond with 'yes/no' or 'y/n'.")

    def selectlist(self, line, input_list):
        answers = []

        if input_list != []:
            i = 1
            for item in input_list:
                self.output(str(i) + ": " + str(item))
                i = i + 1
        else:
            return answers

        choice = self.input(line)
        if not choice:
            return answers

        answers = (choice.replace(' ', '')).split(',')
        return answers

    def input(self, line):
        '''Formats and presents an input request to the user'''
        s = '%s[?]%s %s' % (Colors.O, Colors.N, line)
        answer = raw_input(s)
        return answer

    def heading(self, line):
        '''Formats and presents styled header text'''
        self.output(self.ruler * len(line))
        self.output(line.upper())
        self.output(self.ruler * len(line))

    def print_list(self, title, _list):
        self.heading(title)
        if _list != []:
            for item in _list:
                self.output(item)
        else:
            self.output("None")

# -----------------------------------------------------------------------------
# main test code
# -----------------------------------------------------------------------------
