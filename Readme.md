# Readme

These code are for the assignment 1, COMP9331. In this project, a simple distribute hash table is implemented. 

## Description

These code implemented a simple distribute hash table and corresponding operation, including:

+ a single node can join, leave system
+ each node will send heartbeat packets to detect abrupt leave
+ each node can upload, download and search file stored in the DHT

For detailed description, please read file `Assignment_3331_9331_20T1_updated_ver.pdf`.

## Demonstration

The following content are mainly about how to get these code run. And also a test bash script.

### Running

Make sure the DHTNode.py and the p2p.py are in the same directory. The python version is python3.7.3.

You can run p2p.py by using

```bash
# init command
# <Request type> <Peer ID> <First successor> <Second Successor> <Ping interval>
python3 p2p.py init 2 4 5 10

# join command
# <Request type> <Peer ID> <Known node> <Ping interval>
python3 p2p.py join 6 2 10
```



The time interval when a peer will be regard as abrupt left is 2 * ping interval + 15 seconds. Please don't set a very large ping interval.

### Test script

I wrote a bash script to simplify the test. This script will **remove all the txt file in current path** and then generate 12 txt files with random name between 0 and 9999. You can also specify the number of peers. The peer ID is random generated.

To use this script, you have to grant permission by typing `chomod u+x run.sh`.

And then type

```bash
./run.sh [ping interval] [number of peers]
```
`pingInterval` have to be set and the `number of peers` is optional. If `number of peers` is not given, default value will be set which is the same as the marking rubric.



Here is an example with 20 ping interval and 4 random peers :

```bash
(buster)wangwei@localhost:~/Desktop/final$ ./run.sh 20 4

file names are:
5391 7549 3435 2299 5852 6377 6915 5083 1430 5390 4818 3185 

Random peers are:
47 155 184 217 47 155 
```

Which stands for a peer-to-peer network 47-155-184-217-47-155



Here is an example with 10 ping interval and default peers:

```bash
(buster)wangwei@localhost:~/Desktop/final$ ./run.sh 10

file names are:
422 9270 1994 4405 7398 8541 7366 2163 6182 3886 2511 2743
```



To kill all the xterms, run `./killXterm.sh`.

