Link_state_Routing

Implemented Features：

Correct operation of the link state protocol 

Mechanism to restrict link-state broadcasts 

Appropriate handling of dead nodes, whereby the least-cost paths are updated to reflect the change in topology 

Detect the id and port number of the dead node that joins back 

Other nodes can detect the node when a dead node joins back the topology 
 

To deal with node failures, in update graph function, if another node information has 
not updated in 3 second, the node is removed. Neighbors of failed node can detect node 
failure and they will broadcast this info to their neighbors. 
To Restricting Link-state Broadcasts, in transmit message function, we transmit route 
to in direct connected neighbors. For example, A->B->C, B will transmit A’s route to C. 
In receive excessive link-state broadcast case, when D also received packet from A, and 
will send it to B(A->D->B). B will not send it to C because C has already recorded it in 
function. 
