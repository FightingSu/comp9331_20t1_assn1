from DHTNode import DHTNode
import sys


def main():

    requestType = sys.argv[1]
    ID = ""
    firstSuccessor = ""
    secondSuccessor = ""
    pingInterval = ""
    knownNode = ""

    requestType = requestType.lower()

    ID = sys.argv[2]
    if requestType == "init":
        firstSuccessor = sys.argv[3]
        secondSuccessor = sys.argv[4]
        pingInterval = sys.argv[5]
        node = DHTNode(int(ID), int(pingInterval))
        node.start("init", fst=int(firstSuccessor), snd=int(
            secondSuccessor))

    elif requestType == "join":
        knownNode = sys.argv[3]
        pingInterval = sys.argv[4]
        node = DHTNode(int(ID), int(pingInterval))
        node.start("join", knownNode=int(knownNode))


if __name__ == "__main__":
    main()
