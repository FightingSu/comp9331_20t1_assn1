from time import sleep, time_ns
from queue import Queue
from threading import Thread, RLock
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR

import sys
import os

# all port are calculated based on __basePort
basePort = 12000

# calculate corresponding port
# both reqData and DHTNode knows the way we
# calculate the port from given nodeID


def toPort(knownNode):
    return basePort + knownNode + 1

# a data class for data transferring


class reqData(object):
    def __init__(self, opr: str, src: int, dst: int, content="", stamp=time_ns()):
        # operation:
        # ping - ping other nodes
        # join quit abrupt - a node join or quit(graceful) the DHT
        # store request transfer - insert or retrive data
        # update exit - send message to inform update
        self.opr = opr

        # where did this request came from
        self.src = src

        # the destination of this request
        self.dst = dst

        # data within the request
        self.content = content

        # a unique ID for a request
        self.stamp = stamp

    # construct a reqData object frm given string
    @classmethod
    def fromString(cls, sz: str):
        opr, src, dst, content, stamp = sz.split("\r\n")
        return cls(opr, int(src), int(dst), content, int(stamp))

    # transform a reqData object to string
    def toString(self):
        sz = "\r\n".join((self.opr, str(self.src),
                          str(self.dst), self.content, str(self.stamp)))
        return sz

    # return the a dict relating to the content of this req
    def getContent(self):
        kv = dict()
        for s in self.content.split(", "):
            item = s.split(": ")
            kv[item[0]] = item[1]
        return kv

    # execute the request
    def fulfill(self, addr="127.0.0.1"):
        reqSocket = socket(AF_INET, SOCK_STREAM)
        reqSocket.connect((addr, toPort(self.dst)))
        reqSocket.send(self.toString().encode('utf-8'))
        return reqSocket

    # human-readable printing for terminal
    def __str__(self):
        return "Operation: {0}\n".format(self.opr) + \
            "Source: {0}\n".format(self.src) + \
            "Destination: {0}\n".format(self.dst) + \
            "Timestamp: {0}\n".format(self.stamp) + \
            "Content: {0}\n".format(self.content)

# the object stands for the node


class DHTNode(object):
    # constructor
    def __init__(self, ID, pingInterval):
        # Local hash table that this peer keeps
        self.localHashTable = dict()

        # initialize the nodeID
        self._nodeID = ID

        # initialize the firstSuccessor
        self._firstID = 0

        # initialize the secondSuccessor
        self._secondID = 0

        # setup ping interval
        self._pingInterval = int(pingInterval)

        # node socket
        self.__nodeSocket = None

        # a lock for thread
        self.__lock = RLock()

        # countdown for abrupt quit
        self.__lossCount = dict()

        # We uses producer-consumer model for processing request
        # therefore, we need to set up a thread-safe queue
        self._operationQueue = Queue()

        # set up ping listener
        self._pingListenerThread = Thread(
            target=self.__pingListenerLoop, name="ping listener", daemon=True)

        # set up ping sender
        self._pingSenderThread = Thread(
            target=self.__pingSenderLoop, name="ping sender", daemon=True)

        # set up producer thread
        self._producerThread = Thread(
            target=self.__producerLoop, name="producer thread")

        # set up consumer thread
        self._consumerThread = Thread(
            target=self.__consumerLoop, name="consumer thread")

        # set up a thread dedicated in listenning user input
        self._commandListenerThread = Thread(
            target=self.__commandListenerLoop, name="command listener")

    # start node service
    def start(self, startType, *, knownNode=None, fst=None, snd=None):

        # TCP socket accepting connection from other nodes
        self.__nodeSocket = socket(AF_INET, SOCK_STREAM)
        self.__nodeSocket.bind(("127.0.0.1", self._nodePort))
        self.__nodeSocket.listen()

        # start with argument init or join
        if startType == "init":
            self._firstID = fst
            self._secondID = snd
        elif startType == "join":
            # send a join request to the known node
            joinSocket = reqData("join", self._nodeID,
                                 knownNode, "_nodeID: {}".format(
                                     self._nodeID)).fulfill()
            reply = str()

            try:
                while True:
                    conn, addr = self.__nodeSocket.accept()
                    reply = conn.recv(4096).decode('utf-8').strip()
                    if reply != "":
                        print("\n ---- Join request has been accepted ----")
                        conn.close()
                        break

            except Exception:
                joinSocket.close()
            finally:
                joinSocket.close()

            content = reqData.fromString(reply).getContent()
            self._firstID = int(content["_firstID"])
            self._secondID = int(content["_secondID"])
            print("My first successor ID is {}".format(self._firstID))
            print("My second successor ID is {}".format(self._secondID))

        # start all the threads
        self._producerThread.start()
        self._consumerThread.start()
        self._pingListenerThread.start()
        self._pingSenderThread.start()
        self._commandListenerThread.start()

        # print log
        print("Start peer {0} at port {1}".format(
            self._nodeID, self._nodePort))
        print("Peer {0} can find first successor on port ".format(self._nodeID)
              + "{0} and second successor on port {1}".format(
            self._firstPort, self._secondPort))

    # terminate the program
    def stop(self):
        # send exit signal to threads
        reqData("exit", self._nodeID, self._nodeID).fulfill()
        print("Depature gracefully :-)")
        return

    # put data into local hash table
    def putData(self, filename):
        print("\n ---- Store {0} request accepted ----".format(filename))
        fileHash = self._toHash(filename)
        if fileHash in self.localHashTable:
            self.localHashTable[fileHash].append(filename)
        elif fileHash not in self.localHashTable:
            self.localHashTable[fileHash] = [filename]

    # find is filename in this peer
    def fetchData(self, filename):
        fileHash = self._toHash(filename)
        if fileHash in self.localHashTable and \
                filename in self.localHashTable[fileHash]:
            return True
        return False

    @property
    def _nodePort(self):
        return toPort(self._nodeID)

    @property
    def _firstPort(self):
        return toPort(self._firstID)

    @property
    def _secondPort(self):
        return toPort(self._secondID)

    # producer thread
    # gets request from self.__nodeSocket
    # and store them into self._operationQueue
    def __producerLoop(self):
        while True:
            conn, addr = self.__nodeSocket.accept()
            conn.settimeout(120)
            try:
                content = conn.recv(4096).decode('utf-8')
                req = reqData.fromString(content)
                self._operationQueue.put((conn, req))

                if req.opr == "exit":
                    break

            except ValueError:
                print("Invalid request!")

    # consumer thread
    # read self._operationQueue and handle these requests
    def __consumerLoop(self):
        while True:
            # print("Checking operation queue....", self._operationQueue.empty())
            # sleep(5)
            if self._operationQueue.empty() is False:
                conn, req = self._operationQueue.get()
                # print(req)
                if req.opr == "store":
                    self.__doStore(req)
                    conn.close()
                elif req.opr == "request":
                    self.__doRequest(req)
                    conn.close()
                elif req.opr == "join":
                    self.__doJoin(req)
                    conn.close()
                elif req.opr == "quit":
                    self.__doQuit(req)
                    conn.close()
                    if self._nodeID == int(req.getContent()["_nodeID"]):
                        self.stop()
                elif req.opr == "abrupt":
                    self.__doAbrupt(req)
                    conn.close()
                elif req.opr == "transfer":
                    self.__doTransfer(req, conn)
                elif req.opr == "update":
                    self.__doUpdate(req)
                    conn.close()
                elif req.opr == "exit":
                    conn.close()
                    break

        return

    # Ping loop
    def __pingSenderLoop(self):
        while True:
            if self._pingListenerThread.is_alive() is False:
                break
            sendSocket = socket(AF_INET, SOCK_DGRAM)
            content = reqData("ping", self._nodeID, self._firstID, stamp=time_ns()
                              ).toString().encode('utf-8')
            sendSocket.sendto(
                content, ("127.0.0.1", basePort + self._firstPort))

            content = reqData("ping", self._nodeID, self._secondID, stamp=time_ns()
                              ).toString().encode('utf-8')
            sendSocket.sendto(
                content, ("127.0.0.1", basePort + self._secondPort))

            print("Ping requests sent to Peers {} and {}".format(
                self._firstID, self._secondID))
            sendSocket.close()
            sleep(self._pingInterval)

    def __pingListenerLoop(self):
        # bind a port for receiving ping
        receiverSocket = socket(AF_INET, SOCK_DGRAM)
        receiverSocket.bind(("127.0.0.1", basePort + self._nodePort))
        while True:
            content, addr = receiverSocket.recvfrom(4096)
            req = reqData.fromString(content.decode('utf-8'))
            print("Ping response received from Peer {}".format(req.src))

            # update the time stamp
            self.__lossCount[req.src] = req.stamp
            currTime = time_ns()
            removeKey = None
            restKey = None

            # check if a peer left abruptly
            # no reply over 30s will be
            # considered left abruptly
            for k, v in self.__lossCount.items():
                if (currTime - v) // 1e9 > 15 + 2 * self._pingInterval:
                    removeKey = k

            if removeKey is not None:
                if len(self.__lossCount) > 2:
                    del self.__lossCount[removeKey]
                else:
                    # handle abrupt leave
                    del self.__lossCount[removeKey]
                    restKey = max(self.__lossCount.keys())
                    print("\n ---- Peer {} no longer alive ----".format(removeKey))
                    # the informer will the first successor of the quit node
                    # the second successor will not send this request
                    if (removeKey > restKey and removeKey < self._nodeID) or\
                        (removeKey < restKey and restKey > self._nodeID) or \
                            (removeKey > restKey and removeKey > self._nodeID and restKey > self._nodeID):
                        # inform the p2p network that one node left abruptly
                        reqData("abrupt", self._nodeID, self._firstID,
                                "_nodeID: {}, _firstID: {}, _secondID: {}, leaveNode: {}".format(
                                    self._nodeID, self._firstID, self._secondID, removeKey
                                )).fulfill()

            removeKey = None
            restKey = None

    def __commandListenerLoop(self):
        while True:
            try:
                command = input().lower()
                command = command.split(" ")
                # quit command, quit gracefully
                if command[0] == "quit":
                    reqData("quit", self._nodeID, self._firstID,
                            "_nodeID: {}, _firstID: {}, _secondID: {}".format(
                                self._nodeID, self._firstID, self._secondID)).fulfill()
                    break
                # store command
                # send a file to a peer
                elif command[0] == "store" and len(command) > 1:
                    reqData("store", self._nodeID, self._nodeID,
                            "_nodeID: {}, filename: {}".format(
                                self._nodeID, command[1])).fulfill()
                # request command
                # get file from one peer
                elif command[0] == "request" and len(command) > 1:
                    reqData("request", self._nodeID, self._nodeID,
                            "_nodeID: {}, filename: {}".format(
                                self._nodeID, command[1])).fulfill()
                else:
                    print("Invalid command")
            except Exception:
                print("Invalid command")

    # returns hash number if filename is valid
    # otherwise returns None
    def _toHash(self, filename):
        digit = None
        try:
            digit = int(filename)
            if digit < 0 or digit > 9999:
                raise ValueError
            digit = digit % 256
        except ValueError:
            digit = None
            print("Invalid filename!")
        return digit

    # update the successor and second successor of a peer
    def __doUpdate(self, req):
        self.__lock.acquire()

        print("\n ---- Update request received! ----")
        print("Successor Change request received")
        content = req.getContent()
        self._firstID = int(content["_firstID"])
        self._secondID = int(content["_secondID"])
        print("My first successor ID is {}".format(self._firstID))
        print("My second successor ID is {}".format(self._secondID))

        self.__lock.release()

    def __doJoin(self, req):
        joinNode = int(req.getContent()["_nodeID"])

        # found where to join!
        if (((self._nodeID > self._firstID) and (joinNode > self._nodeID or joinNode < self._firstID)) \
                or (joinNode > self._nodeID and joinNode < self._firstID)) and req.src != joinNode:
            # print log
            print("\n ---- Peer {} join request received! ----".format(joinNode))
            self.__lossCount = dict()

            # response the join node
            reqData(
                "update", self._nodeID, joinNode,
                "_nodeID: {}, _firstID: {}, _secondID: {}".format(
                    self._nodeID, self._firstID, self._secondID)).fulfill()

            # set new successor
            # self._secondID = self._firstID
            # self._firstID = joinNode
            # print("My new first successor is Peer {}".format(
            #     self._firstID))
            # print("My new second successor is Peer {}".format(
            #     self._secondID))

            # update itself
            reqData(
                "update", self._nodeID, self._nodeID,
                "_nodeID: {}, _firstID: {}, _secondID: {}".format(
                    self._nodeID, joinNode, self._firstID)).fulfill()

            # inform other nodes to update them selves
            
            reqData(
                "update", self._nodeID, req.src,
                "_nodeID: {}, _firstID: {}, _secondID: {}".format(
                    self._nodeID, self._nodeID, joinNode)).fulfill()
            print("\n")
        else:
            # pass the request to successor
            print("Peer {} join request forward to my successor".format(
                joinNode))
            req.dst = self._firstID
            req.src = self._nodeID
            req.fulfill()

    def __doQuit(self, req):
        content = req.getContent()
        quitNode = int(content["_nodeID"])
        fstNode = int(content["_firstID"])
        sndNode = int(content["_secondID"])

        if quitNode in self.__lossCount:
            del self.__lossCount[quitNode]

        # all nodes know this node is leaving
        if self._nodeID == quitNode:
            return

        reqData("quit", self._nodeID,
                self._firstID, req.content).fulfill()

        # the pre-predecesor of leaving node
        # send an update request to itself
        if self._secondID == quitNode:
            print("\n ---- Peer {0} will depart from network ----".format(quitNode))
            reqData("update", self._nodeID, self._nodeID,
                    "_nodeID: {0}, _firstID: {1}, _secondID: {2}".format(
                        quitNode, self._firstID, fstNode
                    )).fulfill()
        # the predecesor of leaving node
        # send an update request to itself
        elif self._firstID == quitNode:
            print("\n ---- Peer {0} will depart from network ----".format(quitNode))
            reqData("update", self._nodeID, self._nodeID,
                    "_nodeID: {0}, _firstID: {1}, _secondID: {2}".format(
                        quitNode, fstNode, sndNode
                    )).fulfill()

    def __doAbrupt(self, req):
        quitNode = int(req.getContent()["leaveNode"])
        informer = int(req.getContent()["_nodeID"])

        # the informer will be the first successor of the quit node
        # the second successor will not send this request
        if informer == self._secondID:
            # update itself
            reqData("update", self._nodeID, self._nodeID, "_firstID: {}, _secondID: {}".format(
                self._secondID, req.getContent()["_firstID"]
            )).fulfill()
            # update the other predecessor
            reqData("update", self._nodeID, req.src, "_firstID: {}, _secondID: {}".format(
                self._nodeID, informer
            )).fulfill()

        elif informer != self._nodeID and self._firstID != quitNode:
            req.src = self._nodeID
            req.dst = self._firstID
            req.fulfill()

        return

    def __doStore(self, req):
        filename = req.getContent()["filename"]
        fileHash = self._toHash(filename)

        if fileHash == None:
            return

        # This is the peer which should keep track of this file
        if (fileHash >= req.src and fileHash <= self._nodeID) or \
                (req.src > self._nodeID and (fileHash > req.src or fileHash <= self._nodeID)):
            self.putData(filename)
        else:
            print(
                "Store {0} request forwarded to my successor".format(filename))
            reqData("store", self._nodeID,
                    self._firstID, req.content).fulfill()

    def __doRequest(self, req):
        filename = req.getContent()["filename"]
        fileHash = self._toHash(filename)
        fileData = False

        if fileHash is None:
            return

        # request sent to the smallest peer
        if (fileHash >= req.src and fileHash <= self._nodeID) or \
                (req.src > self._nodeID and (fileHash > req.src or fileHash <= self._nodeID)):
            fileData = self.fetchData(filename)
        else:
            print("File is not here, request for file: {0}, request has been sent to my successor".format(
                filename))
            reqData("request", self._nodeID,
                    self._firstID, req.content).fulfill()
        fullPath = os.getcwd() + "/"
        if fileData is True:
            files = os.listdir()
            files = [x.split(".") for x in files]
            for x in files:
                if x[0] == filename:
                    filename = ".".join(x)
                    fullPath = fullPath + filename

            dstPeer = int(req.getContent()["_nodeID"])
            print("\n ---- File {0} is stored here! ----".format(filename))
            print("Sending file {0} to Peer {1}...".format(
                filename, dstPeer))
            t = reqData("transfer", self._nodeID, dstPeer,
                        "_nodeID: {0}, filename: {1}".format(
                            self._nodeID, filename))
            transferSocket = t.fulfill()
            sleep(3)
            with open(fullPath, "rb") as file:
                while True:
                    fileData = file.read(2048)
                    if fileData:
                        transferSocket.send(fileData)
                    else:
                        print("The file has been sent")
                        break
            transferSocket.close()

    def __doTransfer(self, req, conn):
        print("\n ---- Transfer request received! ----")
        srcPeer = req.getContent()["_nodeID"]
        filename = req.getContent()["filename"]
        print("Peer {0} had file {1}".format(srcPeer, filename))
        print("Receiving File {0} from Peer {1}...".format(filename, srcPeer))
        filename = "received_" + filename
        with open(os.getcwd() + "/" + filename, "wb") as file:
            while True:
                fileData = conn.recv(2048)
                if fileData:
                    file.write(fileData)
                else:
                    print("File {0} received".format(filename))
                    break
        conn.close()
