import hou
import json
import os
import getpass
from settings import SHADERS_SAVE_BASE


def getparm(myparm):
    try:
        myvar = myparm.unexpandedString()
    except hou.OperationFailed:
        try:
            myvar = myparm.expression()
        except hou.OperationFailed:
            myvar = myparm.eval()
    return myvar


def write_parm_data(mynode, parm):
    sspath = os.path.join(SHADERS_SAVE_BASE, os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '_shaders', 'parms')
    if not os.path.exists(sspath):
        os.makedirs(sspath)
    # Execute asCode and write the output script to file.
    mypath = os.path.join(sspath, mynode.parent().parent().name() + '_' + mynode.name() + '_' + parm.name() + '.py')
    if parm != parm.getReferencedParm():
        mynothing = None
    elif 'ch(' in str(getparm(parm)) or 'chs(' in str(getparm(parm)):
        mynothing = None
    else:
        script = parm.asCode()
        f = open(mypath, "w")
        f.write(script)
        f.close()


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
        write_parm_data(childnode, p)
        val = getparm(p)
        interdict[p.name()] = None
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


def getnodedata(nodes=[]):
    mydict = {}
    mydict['scenefile'] = hou.hipFile.name()
    if nodes:
        for node in nodes:
            childnodes = recursenodes(list(node.children()), [])
            topdict = {}
            numnodes = len(childnodes) * len(nodes)
            newcount = 1
            with hou.InterruptableOperation("Retrieving Data", open_interrupt_dialog=True) as progbar:
                for childnd in childnodes:
                    topdict[childnd.name()] = nodedict(childnd)
                    percent = float(newcount) / float(numnodes)
                    progbar.updateProgress(percent)
                    newcount += 1
            mydict[node.name()] = topdict
    return mydict


def recursenodes(nodes, mylist):
    if nodes:
        for child in nodes:
            nodes.remove(child)
            mylist.append(child)
            if child.isLocked() or child.type().definition() is not None:
                print child.name(), '---- #### LOCKED ### OR HDA -----'
            else:
                nodes = nodes + list(child.children())
        recursenodes(nodes, mylist)
    return mylist


def write_data(mynodes=None):
    # writebase = os.path.join(SHADERS_SAVE_BASE, os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '_shaders')
    pathsplit = os.path.dirname(hou.hipFile.name()).split('/')
    writebase = '/'.join([pathsplit[0], pathsplit[1], 'data', 'user', getpass.getuser(),
                          os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '_shaders'])
    if not os.path.exists(writebase):
        os.makedirs(writebase)
    writepath = os.path.join(writebase, os.path.basename(os.path.splitext(hou.hipFile.name())[0]) + '.json')
    with open(writepath, 'w') as f:
        json.dump(getnodedata(mynodes), f)
