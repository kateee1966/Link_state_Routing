# coding=utf8
import sys
import json
import time
import socket
import traceback
import threading

UPDATE_INTERVAL = 1
ROUTE_UPDATE_INTERVAL = 30
NODE_EXPIRE_TIME = 3
DEBUG_MODE = False

'''
Graph Entity class to load telology
Format:
graphentity = {'A': {'B': 6.5, 'F': 2.2},
               'B': {'A': 6.5, 'C': 1.1, 'D': 1.6, 'E':3.2},
               ...
              }
    
'''   
class GraphEntity(object):
    def __init__(self):
        self.nodeentitys = dict()
        self.timeOfUpdate = dict()

    def get_nodeentity(self, nodeentity_id):
        if nodeentity_id not in self.nodeentitys.keys():
            debug('nodeentity not found, id:', nodeentity_id)
            return None
        return self.nodeentitys[nodeentity_id]
        
    def get_nodeentity_neighbours(self, nodeentity_id):
        if nodeentity_id not in self.nodeentitys.keys():
            return []
        if self.nodeentitys[nodeentity_id].neighbours is None:
            return []
        return self.nodeentitys[nodeentity_id].neighbours
        
    def get_graphentity(self):
        graphentity_dict = dict()
        for n_id in self.nodeentitys:
            if n_id not in self.nodeentitys.keys():
                continue
            nodeentity = self.get_nodeentity(n_id)
            if nodeentity.neighbours:
                graphentity_dict[n_id] = nodeentity.neighbours
        return graphentity_dict
        
    def add_nodeentity(self, nodeentity):
        self.nodeentitys[nodeentity.id] = nodeentity
        self.timeOfUpdate[nodeentity.id] = time.time()

    def set_nodeentity(self, nodeentity):
        self.nodeentitys[nodeentity.id] = nodeentity
        self.timeOfUpdate[nodeentity.id] = time.time()

    def set_nodeentity_status(self, nodeentity_id, status):
        self.nodeentitys[nodeentity_id] = status
        self.timeOfUpdate[nodeentity_id] = time.time()  

    '''
    To remove nodeentity from graphentity 
    if it didnot update over NODE_EXPIRE_TIME
    '''
    def update_graphentity(self):
        expire_nodeentitys = []
        for nodeentity_id in self.nodeentitys.keys():
            if nodeentity_id == NODE_ID:
                continue
            if self.timeOfUpdate[nodeentity_id] + NODE_EXPIRE_TIME < time.time():
                expire_nodeentitys.append(nodeentity_id)

        for n_id in expire_nodeentitys:
            del self.nodeentitys[n_id]
            for nn in self.nodeentitys.values():
                if n_id in nn.neighbours.keys():
                    del nn.neighbours[n_id]
                if n_id in nn.neighbour_ports.keys():
                    del nn.neighbour_ports[n_id]
                    
            del self.timeOfUpdate[n_id]

    def __repr__(self):
        return 'graphentity:' + self.nodeentitys
        

'''
NODE ENTITY CLASS
Format:
'nodeentity[ id:' ' | port:'' | status:' ' | neighbours: ' ' ]'
'''
class NodeEntity(object):
    def __init__(self, id, port, neighbours, neighbour_ports, status=False):
        self.status = status
        self.id = id
        self.neighbours = neighbours
        self.port = str(port)                   
        self.neighbour_ports = neighbour_ports  
    
    def get_neighbour_cost(self, nentity_id):
        if nentity_id not in self.neighbours.keys():
            return -1
        return self.neighbours[nentity_id]
        
    def get_neighbour_ports(self, nentity_id):
        if nentity_id not in self.neighbour_ports.keys():
            debug("error, get_neighbour_ports, nodeentityentity not found.")
            return None
        return self.neighbour_ports[nentity_id]
        
    def set_status(self, status):
        self.status = status

    def set_neighbour_cost(self, nentity_id, value):
        self.neighbours[nentity_id] = value

    def set_neighbour_ports(self, neighbour_ports):
        self.neighbour_ports = neighbour_ports

    def is_neighbour(self, nentity_id):
        return nentity_id in self.neighbours

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return 'nodeentity[ id:' + self.id + ' | port:' + self.port + ' | status:' + str(
            self.status) + ' | neighbours: ' + str(self.neighbours) + ' ]'




'''
encode message format: 
nid, neighbour, nodeFrom
'''
def encodeMessage(nodeentity_id, neighbours, ports, from_nodeentitys):
    messageDict = dict()
    messageDict['nodeId'] = nodeentity_id    
    messageDict['nodePort'] = ports
    messageDict['nodeFrom'] = from_nodeentitys
    messageDict['nodeNeighbour'] = neighbours
    return json.dumps(messageDict).encode()


'''
decode msg from socket, byte -> json -> dict.
return nodeentity_id, neighbours
'''
def decodeMessage(data):
    messageDict = json.loads(data.decode())
    return messageDict

'''
############################## send thread ##############################
'''

'''
To get target port
'''
def sendLinkStatePacket(ports, data, rcvfrom):
    for target in ports:
        if str(rcvfrom) != str(target):
            addr = ('127.0.0.1', int(target))
            sock.sendto(data, addr)
            debug('send nodeentity:', NODE_ID, 'data:', data, 'to:', addr)
    return


def send_node_self():
    neighbours = graphentity.get_nodeentity_neighbours(NODE_ID)
    ports = graphentity.get_nodeentity(NODE_ID).neighbour_ports
    from_nodeentitys = [NODE_ID]
    data = encodeMessage(NODE_ID, neighbours, ports, from_nodeentitys)
    sendLinkStatePacket(ports.values(), data, None)
    return


'''
To restrict, transmit route to indirect connected neighbours.
'''
def transmitMessage(messageDict):
    nodeentity_origin_id = messageDict['nodeId']
    from_nodeentitys = messageDict['nodeFrom']
    self_neighbours = graphentity.get_nodeentity_neighbours(NODE_ID)
    ports = []

    for nid in self_neighbours:
        #  make sure it is origin sender.
        if nid == nodeentity_origin_id:
            continue
        #  make sure it is already through nodeentity.
        if nid in from_nodeentitys:
            continue
        n_nodeentity = graphentity.get_nodeentity(nid)
        if n_nodeentity is None:
            continue
        #  make sure current neighbour nodeentity has connection with origin nodeentity.
        if n_nodeentity.is_neighbour(nodeentity_origin_id):
            continue
            
        ports.append(n_nodeentity.port)
    if ports:
        from_nodeentitys.append(NODE_ID)
        data = encodeMessage(nodeentity_origin_id, messageDict['nodeNeighbour'], messageDict['nodePort'], from_nodeentitys)
        sendLinkStatePacket(ports, data, None)

def send_loop():
    while not stop_thread:
        time.sleep(UPDATE_INTERVAL)
        send_node_self()
    return

'''
########################### listen thread ##############################
'''

def packet_wait_thread():
    while not stop_thread:
        try:
            data, (ip, port) = sock.recvfrom(2048)
            messageDict = decodeMessage(data)
            debug('[rcv] current:', NODE_ID, 'data:', data, 'from port:', port, 'nodeentity_from', messageDict['nodeFrom'])
            nodeentity = NodeEntity(messageDict['nodeId'], port, messageDict['nodeNeighbour'], messageDict['nodePort'])
            debug('rcv nodeentity', nodeentity)
            if nodeentity not in graphentity.nodeentitys.values():
                graphentity.add_nodeentity(nodeentity)
            else:
                graphentity.set_nodeentity(nodeentity)
            transmitMessage(messageDict)

        except socket.timeout as e:
            print('[wait_thread]', e)

        except Exception as err:
            debug('[wait_thread]', err)
            debug("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
            debug(traceback.print_exc())
            
        graphentity.update_graphentity()

    return
'''
########################### route thread ##############################
'''

def findRoute():
    global graphentity
    while not stop_thread:
        count = 0
        while count < ROUTE_UPDATE_INTERVAL and stop_thread == False:
            time.sleep(1)
            count += 1
        if count == ROUTE_UPDATE_INTERVAL:
            print('#####################################################')
            debug('[graphentity]', graphentity.nodeentitys)
            if len(graphentity.nodeentitys) > 1:
                for n_id in graphentity.nodeentitys.keys():
                    if n_id == NODE_ID:
                        continue
                    calculatePath(n_id)
            else:
                print("[routes] this is the only nodeentity in network")
            print('#####################################################')
            print()
    return

'''
find and print list cost path in required format
'''

def calculatePath(end):
    path, cost = findShortest(graphentity.get_graphentity(), NODE_ID, end)
    path_str = ''
    for p in path:
        path_str += str(p)
    print('Least cost path to router', str(end), ':', path_str, 'and the cost is', round(float(cost),1))

def dijkstra(graphentity_dict, start, end):

    if start not in graphentity_dict:
        raise ValueError('missing {0}'.format(start))
    if end not in graphentity_dict:
        raise ValueError('missing {0}'.format(end))

    nodeentitys = []
    for key in graphentity_dict.keys():
        nodeentitys.append(key)

    f = float('inf')
    dist_from_start = {n: f for n in nodeentitys}
    dist_from_start[start] = 0
    predecessors = {n: None for n in nodeentitys}

    while len(nodeentitys) > 0:
        candidates = {n: dist_from_start[n] for n in nodeentitys}
        closest = min(candidates, key=candidates.get)

        for n in graphentity_dict[closest]:
            if n not in dist_from_start:
                msg = 'missing nodeentity {0} (neighbor of {1})'.format(n, closest)
                raise ValueError(msg)
            dist_to_n = graphentity_dict[closest][n]
            if dist_to_n < 0:
                msg = 'negative distance from {0} to {1}'.format(closest, n)
                raise ValueError(msg)
            d = dist_from_start[closest] + dist_to_n
            if dist_from_start[n] > d:
                dist_from_start[n] = d
                predecessors[n] = closest

        nodeentitys.remove(closest)

    return dist_from_start, predecessors


def findShortest(graphentity_dict, start, end):
    distances, predecessors = dijkstra(graphentity_dict, start, end)

    if predecessors[end] is None and start != end:
        return [], distances[end]

    path = [end]
    while path[-1] != start:
        path.append(predecessors[path[-1]])
    path.reverse()

    return path, distances[end]
'''
read config file to load required info in graph entity 
'''
def init_graphentity(graphentity, config, id, port):
    with open(config) as f:
        lines = f.readlines()

    lines = [line.rstrip('\n') for line in lines]
    debug(lines)
    #num_neighbours = int(lines[0])
    num_neighbours = int(lines[1])
    debug(num_neighbours)
    neighbours_dict = dict()
    neighbour_ports_dict = dict()
    for i in range(2, num_neighbours + 2):
        tmp = lines[i].split()
        neighbours_dict[tmp[0]] = float(tmp[1])
        neighbour_ports_dict[tmp[0]] = tmp[2]
    nodeentity = NodeEntity(id, port, neighbours_dict, neighbour_ports_dict)
    graphentity.add_nodeentity(nodeentity)
    debug(nodeentity.neighbours)
    debug(neighbours_dict)
    debug(nodeentity)
    
'''
Help to debug, create by me
'''
def debug(*args):
    if DEBUG_MODE:
        msg = ''
        for arg in args:
            msg += ' ' + str(arg)
        print('[DEBUG]', msg)
        
# find node port from config file 
def getnodeentityport (CONFIG_TXT):
    f=open(CONFIG_TXT)
    fline=f.read()
    ffline = fline.split()
    portnum = ffline[1]
    return portnum
    
# find node id from config file 
def getnodeentityid (CONFIG_TXT):
    f=open(CONFIG_TXT)
    fline=f.read()
    ffline = fline.split()
    portid = ffline[0]
    return portid
   
try:    
    CONFIG_TXT = sys.argv[1]
    NODE_ID = getnodeentityid(CONFIG_TXT)
    NODE_PORT = int(getnodeentityport(CONFIG_TXT))
    debug(NODE_ID, NODE_PORT, CONFIG_TXT)
except Exception as e:
    print(e)
    print("invalid input arguments, usage:")
    print("python lsr nodeentity_id nodeentity_port config")
    sys.exit(1)

# create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(NODE_EXPIRE_TIME)
sock.bind(("", int(NODE_PORT)))

# create graphentity.
graphentity = GraphEntity()
init_graphentity(graphentity, CONFIG_TXT, NODE_ID, NODE_PORT)

# create thread flag
stop_thread = False

# print required node info(i.e. id)
print('I am Router ', NODE_ID)

send_node_self()
send_thread = threading.Thread(target=send_loop)
send_thread.start()
listen_thread = threading.Thread(target=packet_wait_thread)
listen_thread.start()
route_thread = threading.Thread(target=findRoute)
route_thread.start()

'''
To make node failed if ctrl+C is pressed
'''
try:
    while 1:
        next
except KeyboardInterrupt:
    stop_thread = True
    send_thread.join()
    listen_thread.join()
