import hou
import json
import os
import getpass
from collections import deque

# from settings import SPECIAL_PARMS
SPECIAL_PARMS = {'mainDoOpacity': 'OpacEnable'}
SPECIAL_TYPES = {'AXIS_Shading_Model_V3': ' AXIS_Shading_Model_V4'}
GRAY, BLACK = 0, 1

def getparm(myparm):
    try:
        myvar = myparm.unexpandedString()
    except hou.OperationFailed:
        try:
            myvar = myparm.expression()
        except hou.OperationFailed:
            myvar = myparm.eval()
    return myvar


def nodedict(childnode):
    interdict = {}
    poss_depend = childnode.inputs()
    if poss_depend:
        interdict['inputs'] = [x.name() for x in poss_depend if x]
    else:
        interdict['inputs'] = []
    poss_depend = childnode.outputs()
    if poss_depend:
        interdict['outputs'] = [x.name() for x in poss_depend if x]
    else:
        interdict['outputs'] = []
    if childnode.parent():
        interdict['parent'] = childnode.parent().path()
    for p in childnode.parms():
        val = getparm(p)
        interdict[p.name()] = val
    interdict['typename'] = childnode.type().name()
    interdict['parenttypename'] = childnode.parent().type().name()
    interdict['amilocked'] = False
    interdict['amihda'] = False
    if childnode.isLocked():
        interdict['amilocked'] = True
    else:
        if childnode.type().definition() is not None:
            interdict['amihda'] = True
    return interdict


def getnodedata(nodes):
    mydict = {}
    if nodes:
        for node in nodes:
            childnodes = node.allSubChildren()
            topdict = {}
            numnodes = len(childnodes) * len(nodes)
            newcount = 1
            with hou.InterruptableOperation("Matching Data", open_interrupt_dialog=True) as progbar:
                for childnd in childnodes:
                    topdict[childnd.name()] = nodedict(childnd)
                    percent = float(newcount) / float(numnodes)
                    progbar.updateProgress(percent)
                    newcount += 1
            mydict[node.name()] = topdict
    return mydict


def read_parm_data(mynode, parm):
    pathsplit = os.path.dirname(hou.hipFile.name()).split('/')
    sspath = '/'.join([pathsplit[0], pathsplit[1], 'data', 'user', getpass.getuser(),
                       os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '_shaders', 'parms'])
    nodename = mynode.parent().parent().name() + '_' + mynode.name()
    mypath = '/'.join([sspath, nodename + '_' + parm.name() + '.py'])
    if 'ch(' in str(getparm(parm)) or 'chs(' in str(getparm(parm)):
        print '---- Avoiding setting on ch or chs ----'
    else:
        if parm != parm.getReferencedParm():
            print '---- Cannot set on -', parm.name(), ' ----'
        elif os.path.exists(mypath):
            # print '---- running this - ', mypath, ' ----'
            execfile(mypath)
    if parm.name() in SPECIAL_PARMS:
        testpath = '/'.join([sspath, nodename + '_' + SPECIAL_PARMS[parm.name()] + '.py'])
        if os.path.exists(testpath):
            with open(testpath, 'r') as f:
                data = f.read().replace(SPECIAL_PARMS[parm.name()], parm.name())
            import tempfile
            temppath = '/'.join([tempfile.gettempdir(), nodename + '_' + SPECIAL_PARMS[parm.name()] + '.py'])
            with open(temppath, 'w') as f:
                f.write(data)
            print '---- Running this on SPECIAL PARM - ', temppath, ' ----'
            execfile(temppath)


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    #modified = {o: d1[o] for o in intersect_keys if d1[o] != d2[o]}
    modified = {}
    for o in intersect_keys:
        if d1[o] != d2[o]:
            modified[o] = d1[o]
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return [x for x in added], [x for x in removed], modified, same


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


def store_node(node):
        for parm in node.parms():
            write_parm_data(node, parm)


def write_parm_data(mynode, parm):
    # Execute asCode and write the output script to file.
    # mypath = os.path.join(temppathbase, mynode.name() + '_' + parm.name() + '.py')
    pathsplit = os.path.dirname(hou.hipFile.name()).split('/')
    sspath = '/'.join([pathsplit[0], pathsplit[1], 'data', 'user', getpass.getuser(),
                       os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '_shaders', 'parms'])
    mypath = os.path.join(sspath, mynode.name() + '_' + parm.name() + '.py')
    if parm != parm.getReferencedParm():
        mynothing = None
    elif 'ch(' in str(getparm(parm)) or 'chs(' in str(getparm(parm)):
        mynothing = None
    else:
        script = parm.asCode()
        f = open(mypath, "w")
        f.write(script)
        f.close()


def replace_node(node, topdict, keepunlocked):
    myposition = node.position()
    myname = node.name()
    myparent = hou.node(topdict[node.name()]['parent'])
    mytype = topdict[node.name()]['typename']
    if node.type().definition() is None:
        print 'This is not an HDA', node.path()
        innodes = [c for c in node.children() if c.type().name() != 'parameter']
        sortedlist = DetectDepends(innodes, {})
        replace_connect_nodes(sortedlist)
    elif (not node.isLocked() and keepunlocked) or mytype in SPECIAL_TYPES:
        print '----- AM LEAVING THIS NODE IN PLACE - NOT REPLACING IT ----', myname
    else:
        print '-------------------> REPLACING THIS NODE ----------->', node.path()
        node.destroy()
        mynode = myparent.createNode(mytype, myname)
        print 'Just Created - ', mynode.path()
        mynode.setPosition(myposition)
        if not topdict[mynode.name()]['amilocked']:
            mynode.allowEditingOfContents()
        for parm in mynode.parms():
            try:
                if parm.name() in topdict[myname].keys() or parm.name() in SPECIAL_PARMS:
                    read_parm_data(mynode, parm)
            except:
                print '---- Parm gone AWOL! ----'


def clean_dicts(added, modified, removed):
    for item in ['outputs', 'inputs']:
        try:
            added.remove(item)
        except:
            pass
        try:
            removed.remove(item)
        except:
            pass
    return added, modified, removed


def count_items(d):
    sscount = 0
    for key in d.keys():
        newd = d[key]
        for inkey in newd.keys():
            sscount += 1
        # sscount += 1
    return sscount



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
        print hou.node(node).path()
        returnnodes.append(hou.node(node)) # Switching node selection back to object mode
    return depend_dict, returnnodes


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


def add_to_list(l1, l2):
    l3 = []
    for item in l2:
        if item not in l1:
            l3.append(item)
    return l1 + l3


def get_sorted_node_list(topnodes):
    mylist = []
    depend_dict, returnnodes = DetectDepends(topnodes, {})
    mylist = add_to_list(mylist, returnnodes)
    for node in topnodes:
        depend_dict, returnnodes = DetectDepends([c for c in node.children() if c.type().name() != 'parameter'], depend_dict)
        mylist = add_to_list(mylist, reversed(returnnodes))
        for innode in returnnodes:
            depend_dict, returnnodes = DetectDepends([c for c in innode.children() if c.type().name() != 'parameter'], depend_dict)
            mylist = add_to_list(mylist, reversed(returnnodes))
            for ininnode in returnnodes:
                depend_dict, returnnodes = DetectDepends([c for c in ininnode.children() if c.type().name() != 'parameter'], depend_dict)
                mylist = add_to_list(mylist, reversed(returnnodes))
    for item in mylist:
        print item.path()


def read_data():
    if hou.ui.displayMessage("Keep your Unlocked Nodes intact?", buttons=("Yes", "No"),
                             default_choice=0, close_choice=0) == 0:
        keepunlocked = True
    else:
        keepunlocked = False
    allnodes = hou.node('/obj').allSubChildren()
    pathsplit = os.path.dirname(hou.hipFile.name()).split('/')
    readpath = '/'.join([pathsplit[0], pathsplit[1], 'data', 'user',
                         getpass.getuser(), os.path.basename(os.path.splitext(hou.hipFile.name())[0]) +
                         '_shaders', os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '.json'])
    if os.path.exists(readpath):
        with open(readpath, 'r') as f:
            mydict = json.load(f)
        if mydict['scenefile'] == hou.hipFile.name():
            mydict.pop('scenefile', None)
            topnodes = [x for x in mydict.keys()]
            grabnodes = [node for node in allnodes if node.name() in topnodes]
            # get_sorted_node_list(grabnodes)
            newdict = getnodedata(grabnodes)
            total_items = count_items(mydict)
            i = 0
            with hou.InterruptableOperation("Converting Shaders", open_interrupt_dialog=True) as operation:
                for key in mydict.keys():
                    topdict = mydict[key]
                    newtopdict = newdict[key]
                    for childnode in topdict.keys():
                        i += 1
                        added, removed, modified, same = dict_compare(topdict[childnode], newtopdict[childnode])
                        added, modified, removed = clean_dicts(added, modified, removed)
                        if modified or added or removed:
                            replace_node(hou.node(topdict[childnode]['parent'] +
                                                  '/' + childnode), topdict, keepunlocked)
                        percent = float(i) / float(total_items)
                        operation.updateProgress(percent)
        else:
            print '---- This saved data does not belong to this scene! ----'
    else:
        print '----- There is no matching shader data saved for this Scene file! -----'
