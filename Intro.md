## About protocol

To begin with, I have to introduce the detail about the protocol. Basically, this protocol have five fields:

+ Request type
+ Source
+ Destination
+ Time stamp
+ Content

Request type stands for different operations. There are 9 types: `store, request, transfer, join, quit, abrupt, update, exit, ping`. 

+ `Store`, `request` and `transfer` type are used when one tries to insert or retrieve data from DHT. Specially, `transfer` is designed when one file is found and need to be transferred.
+ `join`, `quit` and `abrupt` request are sent when a peer want to join or quit a DHT or a abrupt leave was detected. 
+ `update` is intend to notify one peer to update its successors.
+ `exit` will be sent to peer itself  after it finished notified others that it will quit.
+ `ping` is using to ping successor. It can detect abrupt leave.

Source and destination are peer IDs of the sender and receiver. 

Time stamp is a unique sign of a request

Content are designed to put extra informations in a request. It was present in key-value pairs. I often put the ID of the origin (not source, source is the predecessor of the receiver) of a request into "\_nodeID", which brings me vast convenient.



## About classes

In this assignment, I implemented two classes. The first one was called `reqData` which was dedicated to send and analyze requests. The second one was called `DHTNode` which stands for a peer in the peer-to-peer network. 



### `reqData`

Let's start with the simple one. `reqData` class contains five class members:

```python
# type of operations
self.opr = opr
# where did this request came from
self.src = src
# the destination of this request
self.dst = dst
# data within the request
self.content = content
# a unique ID for a request
self.stamp = stamp
```

Which are introduced above. Let's go to the member functions:

```python
@classmethod
def fromString(cls, sz: str)
def toString(self)
def getContent(self)
def fulfill(self, addr="127.0.0.1")
```

There are four important functions. 

+ `fromString()` constructs a `reqData` object from given string.
+ `getContent()` function returns key-value pairs, helping us to read the extra information.
+ `fulfill()` function sends the request inside of the object based on `self.src` and `self.dst` via TCP

In addition, the request sent by `fulfill()` function will be closed by the destination peer. This is probably the most frequent used function.



### `DHTNode`

`DHTNode` is a class represent a peer in a peer-to-peer network. It uses producer-consumer pattern, which means there is a producer thread accepting requests and there is a consumer thread responding requests. Actually, there are five threads where three of them are producer:

+ `producerThread`: Listening to a socket and put requests into `operationQueue`.
+ `commandListenerThread`: Listen to keyboard and put these requests into `operationQueue`.
+ `pingListenerThread`: Receiving ping message from other peers. If a abrupt leave were detected, it would send a `abrupt` request to its successor.
+ `pingSenderThread`: Send UDP packets with given ping interval.
+ `consumerThread`: Read the `operationQueue` and assign these request into private functions.

So, a `DHTNode` object works as follows: 

+ Construct a `DHTNode` with `ID` and `pingInterval`.
+ Invoke `start()` function to set up first successor and the second successor depending on the type argument. And start listening to a socket then start these five threads. 
+ Get a `KeyboardInterruptException` to quit abruptly or get a `quit` command from Standard I/O to inform other peers that its leaving. After that, send an `exit` request to itself then invoke `stop()`.

During the implementation, I found `reqData` needs more information. So I added a `content` into `reqData` as a class member to store extra information. I often put the origin  (not source, source is the predecessor of the receiver) of a request into `content` field as "\_nodeID", and I also put "\_firstID" and "\_secondID" into `content` field in the `update` request. As for `transfer`, `request`, `store` requests, I put "filename" in the `content` field.



## Improvements

First, the performance of this protocol is very poor. Many requests have to go through the entire peer-to-peer network to be done. I think it can be improved by keeping more successors in one peer like `Chord` did. And also a peer can keep a predecessor as well.  

Second is that I found sometimes two TCP packets may "attached" into one TCP packet may leads to `reqData.fromString()` function failed (`transfer` request and the file data are "thick" together). To solve this problem, I add a `sleep(3)` between `transfer` request and data transfer. Although this solved the problem, its efficiency is not ideal. It can be solved by adding the length of the request head.

















