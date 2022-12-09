import json
import math
import numpy as np
import matplotlib.pyplot as plt

plt.grid(linestyle='--', linewidth=0.5)
plt.gca().set_aspect('equal', adjustable='box')

#Load Bridge Data
try:
    f = open('TestBridgeData1.json')
except:
    raise Exception("No bridge data file could be found.")
else:
    data = json.load(f)
    f.close()

def preRunBridgeChecker():
    print("Running Pre-run Bridge Checks...")
    numOfNodes = len(data["Nodes"])
    numOfMembers = len(data["Members"])
    numOfLoads = len(data["Loads"])
    numOfFixedNodes = 0
    numOfRollingNodes = 0

    for node in data["Nodes"]:
        if node["fixedNode?"] and node["rollingNode?"]:
            raise Exception('Nodes cannot be fixed and rolling, make sure your anchored nodes are fixed OR rolling.')
        elif node["fixedNode?"]:
            numOfFixedNodes += 1
        elif node["rollingNode?"]:
            numOfRollingNodes += 1

    #Fixed and rolling node error catching
    if numOfFixedNodes > 1:
        raise Exception('This simulation does not support more than one fixed node at a time.')
    elif numOfFixedNodes < 1:
        raise Exception('This simulation requires at least one fixed node.')
    if numOfRollingNodes > 1:
        raise Exception('This simulation does not support more than one rolling node at a time.')
    elif numOfRollingNodes < 1:
        raise Exception('This simulation requires at least one rolling node.')

    #Member error catching
    if numOfNodes*2 > numOfMembers+3:
        raise Exception(f'There are too little members, try adding {(numOfNodes*2)-(numOfMembers+3)} more.')
    elif numOfNodes*2 < numOfMembers+3:
        raise Exception(f'There are too many members, try removing {(numOfMembers+3)-(numOfNodes*2)} more.')
    
    #Load error catching
    loadNodes = []
    for load in data["Loads"]:
        loadNodes.append(load["loadNode"])
    if sorted(loadNodes) != sorted(list(set(loadNodes))):
        raise Exception('There can only be a maximum of one load per node, make sure there isn\'t more than one load per node')
    if numOfLoads <= 0:
        raise Exception('There are no loads on the bridge, try adding some.')

def main():

    #plot nodes
    for node in range(1, len(data["Nodes"])+1):
        plotNode(node)

    #plot members
    for member in data["Members"]:
        pass
        #plotMember(member)

    #Add and label loads
    for load in data["Loads"]:
        plotLoad(load)
    
    trussAngleMatrix = np.zeros((len(data["Nodes"])*2, len(data["Members"])+3))
    for member in data["Members"]:
        node1 = member["nodes"][0]
        node2 = member["nodes"][1]
        #get position of both nodes
        #find inverse tan of (y2-y1)/(x2-x1)
        angleToHorizontal = math.atan((nodeInfo(node2).y-nodeInfo(node1).y)/
                                      (nodeInfo(node2).x-nodeInfo(node1).x))
        #get cos and sin of angle
        matrixAngleX = abs(math.cos(angleToHorizontal))
        matrixAngleY = abs(math.sin(angleToHorizontal))
        #Determine positive or negative by the direction of member
        if nodeInfo(node2).x < nodeInfo(node1).x:
            matrixAngleX = -matrixAngleX
        if nodeInfo(node2).y < nodeInfo(node1).y:
            matrixAngleY = -matrixAngleY

        #add to angles matrix
        trussAngleMatrix[(node1-1)*2, member["memberNum"]-1] = matrixAngleX #1 to 2 cos()
        trussAngleMatrix[(node1-1)*2+1, member["memberNum"]-1] = matrixAngleY #1 to 2 sin()
        trussAngleMatrix[(node2-1)*2, member["memberNum"]-1] = -matrixAngleX #2 to 1 cos()
        trussAngleMatrix[(node2-1)*2+1, member["memberNum"]-1] = -matrixAngleY #2 to 1 sin()

    #Adding reaction force angles to angle matrix, all reaction force angles will be completely vertical or horizontal
    ##The last three columns for the matrix will always be ordered {Reaction2y, Reaction1x, Reaction1y}
    for node in constrainedNodes:
        if nodeInfo(node).isFixed:
            trussAngleMatrix[(nodeInfo(node).nodeNum-1)*2, trussAngleMatrix.shape[1]-1] = 1
            trussAngleMatrix[(nodeInfo(node).nodeNum-1)*2+1, trussAngleMatrix.shape[1]-2] = 1
        elif nodeInfo(node).isRolling:
            trussAngleMatrix[(nodeInfo(node).nodeNum-1)*2+1, trussAngleMatrix.shape[1]-3] = 1

    #Inverse the angle matrix (AngleMatrix^-1 * Coeffecients = Forces)
    inverseTrussAngleMatrix = np.linalg.inv(trussAngleMatrix)

    #Make empty list, add load to list, Transpose.
    coeffecientMatrix = np.zeros(len(data["Nodes"])*2)
    for load in data["Loads"]:
        coeffecientMatrix[(load["loadNode"]-1)*2+1] = load["loadForce"]

    trussForceMatrix = inverseTrussAngleMatrix.dot(coeffecientMatrix.T)

    plotTrussForces(trussForceMatrix)

class Node(object):
    def __init__(self, nodeNum):
        self.nodeNum = nodeNum
        self.position = data["Nodes"][nodeNum-1]["cords"]
        self.x = self.position[0]
        self.y = self.position[1]
        self.isFixed = data["Nodes"][nodeNum-1]["fixedNode?"]
        self.isRolling = data["Nodes"][nodeNum-1]["rollingNode?"]

def nodeInfo(nodeNum: int):
    nodeInfo = Node(nodeNum)
    return nodeInfo

constrainedNodes = []

def plotNode(node):
    if nodeInfo(node).isFixed or nodeInfo(node).isRolling:
        plt.plot(nodeInfo(node).x, nodeInfo(node).y, "ko")
        constrainedNodes.append(node)
    else:
        plt.plot(nodeInfo(node).x, nodeInfo(node).y, "bo")

    plt.annotate(node, (nodeInfo(node).x, nodeInfo(node).y), color="m")

def plotMember(member):
    nodeXs = nodeInfo(member["nodes"][0]).x, nodeInfo(member["nodes"][1]).x
    nodeYs = nodeInfo(member["nodes"][0]).y, nodeInfo(member["nodes"][1]).y
    plt.plot(nodeXs, nodeYs, "g") #matplotlib wants a (x, x, ...), (y, y, ...) list for some dumb reason

    centerx, centery = sum(nodeXs)/2, sum(nodeYs)/2 #Midpoint formula
    plt.annotate(member["memberNum"], (centerx, centery), color="c")

def plotLoad(load):
    loadX = nodeInfo(load["loadNode"]).x
    loadY = nodeInfo(load["loadNode"]).y
    plt.arrow(x=loadX, y=loadY,
                dx=0,    dy=-load["loadNode"]/25,
                width=0.03, color="r")
    plt.annotate(load["loadNumber"], (loadX, (loadY+load["loadNode"]/25)/2), color="c")

def plotTrussForces(forces):
    i = 0
    for member in data["Members"]:
        nodeXs = nodeInfo(member["nodes"][0]).x, nodeInfo(member["nodes"][1]).x
        nodeYs = nodeInfo(member["nodes"][0]).y, nodeInfo(member["nodes"][1]).y
        plt.plot(nodeXs, nodeYs, "g") #matplotlib wants a (x, x, ...), (y, y, ...) list for some dumb reason

        centerx, centery = sum(nodeXs)/2, sum(nodeYs)/2 #Midpoint formula
        plt.annotate(round(forces[i], 2), (centerx, centery), color="k")
        i += 1

if __name__=="__main__":
    print("Starting...")
    preRunBridgeChecker()
    main()
    plt.show()