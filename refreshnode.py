import hou
import os
import tempfile
from collections import deque
GRAY, BLACK = 0, 1
temppathbase = tempfile.gettempdir()
# from settings import SPECIAL_PARMS
SPECIAL_PARMS = {'mainDoOpacity': 'OpacEnable'}
SPECIAL_TYPES = {'AXIS_Shading_Model_V3': ' AXIS_Shading_Model_V4'}


def DetectDepends(selnodes, depend_dict):
    for node in selnodes:
        poss_depend = [var for var in list(set(node.inputs())) if var]
        if poss_depend:
            for depend in poss_depend:
                mynodelist = [depend]
                for item in mynodelist:
                    depend_dict.setdefault(node.path(),[]).append(item.path())
        else:
            depend_dict[node.path()] = []
    returnnodes = []
    for node in reversed(topological(depend_dict)):
        returnnodes.append(hou.node(node)) # Switching node selection back to object mode
    return returnnodes


def topological(graph):
    order, enter, state = deque(), set(graph), {}

    def dfs(node):
        state[node] = GRAY
        for k in graph.get(node, ()):
            sk = state.get(k, None)
            if sk == GRAY: raise ValueError("cycle")
            if sk == BLACK: continue
            enter.discard(k)
            dfs(k)
        order.appendleft(node)
        state[node] = BLACK

    while enter: dfs(enter.pop())
    return order


def write_parm_data(mynode, parm):
    # Execute asCode and write the output script to file.
    mypath = os.path.join(temppathbase, mynode.name() + '_' + parm.name() + '.py')
    if parm != parm.getReferencedParm():
        mynothing = None
    elif 'ch(' in str(getparm(parm)) or 'chs(' in str(getparm(parm)):
        mynothing = None
    else:
        script = parm.asCode()
        f = open(mypath, "w")
        f.write(script)
        f.close()


def read_parm_data(mynode, parm):
    mypath = os.path.join(temppathbase, mynode.name() + '_' + parm.name() + '.py')
    if 'ch(' in str(getparm(parm)) or 'chs(' in str(getparm(parm)):
        print '---- Avoiding setting on ch or chs ----'
    else:
        if parm != parm.getReferencedParm():
            print '---- Cannot set on -', parm.name(), ' ----'
        elif os.path.exists(mypath):
            # print '---- running this - ', mypath, ' ----'
            execfile(mypath)
            os.remove(mypath)
    if parm.name() in SPECIAL_PARMS:
        testpath = os.path.join(temppathbase, mynode.name() + '_' + SPECIAL_PARMS[parm.name()] + '.py')
        if os.path.exists(testpath):
            with open(testpath, 'r') as f:
                data = f.read().replace(SPECIAL_PARMS[parm.name()], parm.name())
            import tempfile
            temppath = os.path.join(temppathbase, mynode.name() + '_' + SPECIAL_PARMS[parm.name()] + '.py')
            with open(temppath, 'w') as f:
                f.write(data)
            print '---- Running this on SPECIAL PARM - ', temppath, ' ----'
            execfile(temppath)


def replace_connect_nodes(nodelist):
    newnodes = []
    oldnodes = []
    topdict = {}
    for srcnode in nodelist:
        # Store data off node before killing it
        store_node(srcnode)
        myparent = srcnode.parent()
        myposition = srcnode.position()
        mytype = srcnode.type().name().replace('V3', 'V4')
        myname = srcnode.name()
        myconnections = [connectors[0] for connectors in srcnode.inputConnectors() if len(connectors) != 0]
        # print '----->', myconnections
        mydict = {}
        for cnct in myconnections:
            keyname = str(cnct.inputIndex())
            inputone = int(cnct.inputIndex())
            inputnode = str(cnct.inputNode().path())
            inputtwo = int(cnct.outputIndex())
            mydict[keyname] = [inputone, inputnode, inputtwo]
            print '>>>>', keyname, ':', mydict[keyname]
        topdict[srcnode.name().replace('V3', 'V4')] = mydict
        # End of Store data
        # srcnode.destroy()
        srcnode.setName(srcnode.name() + '_OLD')
        oldnodes.append(srcnode)
        print 'Trying to add node of type ->', mytype
        try:
            tgtnode = myparent.createNode(mytype, 'temp')
            tgtnode.setName(myname.replace('V3', 'V4'))
            newnodes.append(tgtnode)
            tgtnode.setPosition(myposition)
            for parm in tgtnode.parms():
                read_parm_data(tgtnode, parm)
        except:
            print 'Not Able to add node of Type - ', mytype
            srcnode.setName(myname)
            newnodes.append(srcnode)
            oldnodes.remove(srcnode)
    print topdict
    for node in newnodes:
        for key in topdict[node.name()].keys():
            node.setInput(topdict[node.name()][key][0], hou.node(topdict[node.name()][key][1].replace('_OLD', '').replace('V3', 'V4')), topdict[node.name()][key][2])
    for oldnd in oldnodes:
        oldnd.destroy()

def replace_node(node):
    myposition = node.position()
    myname = node.name()
    myparent = node.parent()
    mytype = node.type().name()
    amilocked = node.isLocked()
    if node.type().definition() is None:
        print 'This is not an HDA', node.path()
        innodes = [c for c in node.children() if c.type().name() != 'parameter']
        sortedlist = DetectDepends(innodes, {})
        replace_connect_nodes(sortedlist)
    else:
        try:
            testnode = myparent.createNode(mytype, 'testing')
            testnode.destroy()
            node.destroy()
            mynode = myparent.createNode(mytype, myname)
            mynode.setPosition(myposition)
            if not amilocked:
                mynode.allowEditingOfContents()
            for parm in mynode.parms():
                read_parm_data(mynode, parm)
        except:
            print 'Cannot find definition of this node to replace with!'
            
            
def store_node(node):
        for parm in node.parms():
            write_parm_data(node, parm)   
            

def getparm(myparm):
    try:
        myvar = myparm.unexpandedString()
    except hou.OperationFailed:
        try:
            myvar = myparm.expression()
        except hou.OperationFailed:
            myvar = myparm.eval()
    return myvar
    

def get_parms(node):
    return node.parms()
    

def refreshnodes(nodes):
    numnodes = len(nodes)
    newcount = 1
    with hou.InterruptableOperation("Refreshing Nodes", open_interrupt_dialog=True) as progbar:
        for node in nodes:
            store_node(node)
            replace_node(node)
            percent = float(newcount) / float(numnodes)
            progbar.updateProgress(percent)
            newcount += 1
            
            
# node = hou.selectedNodes()[0]
# innodes = [c for c in node.children() if c.type().name() != 'parameter']
# sortedlist = DetectDepends(innodes, {})
# replace_connect_nodes(sortedlist)
# refreshnodes(hou.selectedNodes())
