import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring
import os;
from pprint import pprint
import json
from json import dumps, loads, JSONEncoder, JSONDecoder
import pickle

class PythonObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (list, dict, str, unicode, int, float, bool, type(None))):
            return JSONEncoder.encode(self, obj)
        elif isinstance(obj, set):
            return JSONEncoder.encode(self, list(obj)) #str(obj) #"set([{}])".format(",".join([ PythonObjectEncoder.default(self,i) for i in list(obj)]))
        return pickle.dumps(obj)

############# hirarchical model ##############

class mh_base(object):
    def __init__(self,args,n,m,xml,tags=[],attrs=[],depth=0):
        super(mh_base,self).__init__()
        self.args = args
        self.n = n
        self.m = m;
        self.xml = xml;
        self.tags = [n]+tags 
        self.attrs = attrs
        self.depth = depth
        self.addnew = 0
        
    def __getattr__(self,n):
        if n in self.attrs:
            if n in self.xml.attrib:
                return self.xml.attrib[n]
            return None
        else:
            #print(str(self))
            raise AttributeError
    def setxml(self,n,v):
        if n in self.attrs:
            if self.addnew or (n in self.xml.attrib):
                self.xml.attrib[n] = v
        else:
            raise AttributeError
    def addxml(self,n,v):
        if n in self.attrs:
            self.xml.attrib[n] = v
        else:
            raise AttributeError
    def match(self, tags):
        for i in tags:
            if i in self.tags:
                return True
        return False
    def get_xml(self):
        return tostring(self.xml).rstrip()
    def shortname(self,args):
        n = self.name
        if not (args.removepath is None):
            n = n.replace(args.removepath,"")
        return n

class mh_scope(mh_base):
    def __init__(self,args,direction,m,depth=0):
        super(mh_scope,self).__init__(args,'_scope_', m, None, ['elem'], depth=depth)
        self.direction = direction

class mh_remote(mh_base):
    def __init__(self,args,m,xml,depth=0):
        super(mh_remote,self).__init__(args,'remote',m,xml,['elem'],['name','pushurl','review','fetch'],depth=depth)
        if ('fetch' in self.xml.attrib) and ((self.xml.attrib['fetch'].startswith(".."))):
            try:
                self.xml.attrib['fetch']=args.gitbase
            except:
                raise(Exception("Canot find gitbase in %s" %(str(args))))

class mh_default(mh_base):
    def __init__(self,args,m,xml,depth=0):
        super(mh_default,self).__init__(args,'default',m,xml,['elem'],['remote','sync-c','sync-j'],depth=depth)
        
        
class mh_project(mh_base):
    def __init__(self,args,m,xml,depth=0):
        super(mh_project,self).__init__(args,'project',m,xml,['elem'],['name','path','revision','remote','upstream','_gitserver_'],depth=depth)
        if 'path' in self.xml.attrib and self.xml.attrib['path'].endswith("/"):
            self.xml.attrib['path'] = self.xml.attrib['path'][:-1]
    def __str__(self):
        return "project name={}".format(self.name)
    def changed(self,p,args):
        return not (self.revision == p.revision)
    def nameorpath(self,args):
        if 'path' in self.xml.attrib:
            return self.xml.attrib['path']
        return self.shortname(args)
    

class mh_remove_project(mh_base):
    def __init__(self,args,m,xml,depth=0):
        super(mh_remove_project,self).__init__(args,'remove_project',m,xml,['elem'],['name'],depth=depth)
    def __str__(self):
        return "remove-project name={}".format(self.name)

class mh_include(mh_base):
    def __init__(self,args,m,xml,depth=0):
        super(mh_include,self).__init__(args,'include',m,xml,['rec'],['name'],depth=depth)
        n = self.name
        if not n.startswith("/"):
            nori = n
            n = os.path.join(os.path.dirname(m.abspath),n);
            if not os.path.isfile(n):
                p = m.m
                while not p is None:
                    n = os.path.join(os.path.dirname(p.ctx['abspath']),nori);
                    print(" > " + n  + " relative to " + p.ctx['abspath'])
                    if os.path.isfile(n):
                        break
                    p = p.m
        self._c = ftomanifest(args,n,m,depth);
    def __str__(self):
        return "include name={}".format(self.name)
        
tags = {
    'include' : mh_include,
    'project' : mh_project,
    'remove-project' : mh_remove_project,
    'remote'  : mh_remote,
    'default' : mh_default
}

class mh_manifest(mh_base):
    def __init__(self,args,ctx,m,xml,depth=0):
        super(mh_manifest,self).__init__(args, 'manifest',m,xml,['rec'],[],depth=depth)
        self.ctx = ctx;
        self._c = [ tags[c1.tag](args,self,c1,depth=self.depth+1) for c1 in [ c0 for c0 in xml if c0.tag in tags ] ]
    def __getattr__(self,n):
        if n in self.ctx:
            return self.ctx[n];
        return mh_base.__getattr__(self,n)
    def __str__(self):
        return "maifest name={}".format(self.abspath)

def ftomanifest(args,n,mp,depth=0):
    if (args.verbose > 0):
        print((" " * depth)+("+%s" %(n)))
    afn = os.path.abspath(n);
    tree = ET.parse(n)
    root = tree.getroot()
    pf = {'abspath': afn }
    return [ mh_scope(args,'enter',pf, depth) ] + \
        [ mh_manifest(args, pf, mp, xml, depth) for xml in root.iter('manifest') ] + \
        [ mh_scope(args,'exit', pf, depth) ];
    
#################################################

class logclass(object):
    def __init__(self, args):
        super(logclass,self).__init__()
        self.args = args
    def log(self,l):
        if not (self.args.log is None):
            with open(self.args.log,"a") as f:
                f.write(l + "\n")

class projar(logclass):
    def __init__(self,up,args):
        super(projar,self).__init__(args)
        self.up = up
        self.args = args
        self.p = []
        self.added = []
    def add(self,e):
        self.p.append(e)
    def uniformname(self,n):
        if not (self.args.removepath is None):
            n = n.replace(self.args.removepath,"")
        return n;
    def rem(self,e):
        self.p = [ p for p in self.p if not (p.shortname(self.args) ==  e.shortname(self.args)) ]
    def projects(self):
        return self.p
    def contain(self,e):
        a = [ p for p in self.p if (p.shortname(self.args) ==  e.shortname(self.args)) ]
        return (len(a) >= 1)
    def changed(self,e):
        a = [ p for p in self.p if (p.shortname(self.args) ==  e.shortname(self.args)) ]
        return a[0].changed(e,self.args)
    def getProject(self,e):
        a = [ p for p in self.p if (p.shortname(self.args) ==  e.shortname(self.args)) ]
        return a[0]
    def addproject(self,p):
        n = norig = p.name
        if not (self.args.removepath is None):
            n = self.args.removepath + norig
        if p.path is None:
            p.addxml('path',norig)
        if p.remote is None and not (self.args.defserver is None):
            p.addxml('remote',self.args.defserver)
        self.log("Add {}".format(n))
        p.setxml('name',n)
        if not (self.up is None):
            self.up.tree[0]._c.append(p)
        
    def updateshawith(self,e):
        a = [ p for p in self.p if (self.uniformname(p.name) ==  self.uniformname(e.name)) ]
        if not (len(a) == 1):
            raise Exception("Project not present");
        self.log("Update {} {}".format(a[0].name, e.revision))
        a[0].setxml('revision',e.revision)


class multirepo(logclass):
    def __init__(self,p,path):
        super(multirepo,self).__init__(p.args)
        self._p = p
        self.path = path
        self.remotes = []
        self.alias = None
        self._id = -1;
        self._ismerged = None
    def addalias(self, a ):
        if (a == self.path):
            return;
        if (self.alias is not None) and (a in self.alias):
            return;
        if (self.alias is None):
            self.alias = [];
        self.alias.append(a);

    def addremote(self, v, url, n, mergefrom=None ):
        for r in self.remotes:
            if r['v'] == v:
                for u in r['urls']:
                    if u['url'] == url and u['n'] == n:
                        return
                r['urls'].append({'url':url,'n':n, 'mergefrom':mergefrom});
                return
        self.remotes.append({'v':v, 'urls':[{'url':url,'n':n,'mergefrom':mergefrom}]});
    def __str__(self):
        return ",".join([ "v:{},urls:{}".format(r['v'],r['urls'])  for r in self.remotes])+",path:"+self.path

    def urlof(self,n,ui):
        v = self.remotes[n]['urls'][ui]
        #print("+++++++ {} {}".format(n,ui) + str(v))
        r = v['url'] + v['n']
        if not (v['n'].startswith("/") or v['url'].endswith("/")):
            r = v['url'] + "/" + v['n']
        return r;

    def clonescript(self):
        if self._ismerged is not None:
            return "";
        cmd = []
        id = self.path.replace("/","_");
        url0 = self.urlof(0,0);
        cmd.append("clone_repo {} {} {}\n".format(id, url0, self.path));
        if self.alias is not None:
            for i in self.alias:
                cmd.append(" clone_alias {} {}\n".format(id, i));
        for i in range(len(self.remotes)):
            cmd.append(" clone_repo_new {} {} {}\n".format(id, self.remotes[i]['v'], self.urlof(i,0)));
            for j in range(1,len(self.remotes[i]['urls'])):
                cmd.append(" clone_repo_more_url {} {} {}\n".format(id, self.remotes[i]['v'], self.urlof(i,j)));
        cmd.append("clone_repo_fetch {} \n".format(id));

        return "".join(cmd);

    def jsonscript(self):
        remotes = []
        for i in range(len(self.remotes)):
            urls = []
            mergefrom = []
            for j in range(0,len(self.remotes[i]['urls'])):
                urls.append(self.urlof(i,j));
                if not (self.remotes[i]['urls'][j]['mergefrom'] is None):
                    mergefrom.append(self.remotes[i]['urls'][j]['mergefrom'])
            urls = list(set(urls))
            v = {'name' : self.remotes[i]['v'], 'urls' : urls }
            if (len(mergefrom) > 0):
                v['mergedfrom'] = mergefrom;
            remotes.append(v)
        d = {   'id' : self.path.replace("/","_"),
                'gerritpath' : self.path,
                'remotes' : remotes }
        if self.alias is not None:
            d['alias'] = self.alias
        if self._ismerged is not None:
            d['ismerged'] = self._ismerged
        return d

class multirepolist(logclass):
    def __init__(self,args):
        super(multirepolist,self).__init__(args)
        self.args = args
        self.p = []
        self.ptop = {}
    def add(self,e):
        e._id = len(self.p)
        self.p.append(e)

    def regProj(self,p):
        if p in self.ptop:
            return self.ptop[p];
        pr = multirepo(self,p);
        self.ptop[p] = pr;
        self.add(pr);
        return pr;
    def __str__(self):
        return "\n".join([str(i) for i in self.p]);

    def clonescript(self):
        i = """#!/bin/bash -x
. "$(dirname $0)/base.sh"
""";
        return i+"\n".join(p.clonescript() for p in self.p);

    def jsonscript(self):
        d = [ p.jsonscript() for p in self.p];
        return json.dumps(d, sort_keys=True, indent=4, separators=(',', ': '), cls=PythonObjectEncoder);

    def merge(self):
        global_alias = {};
        def add_alias(a,b):
            if not (a in global_alias):
                global_alias[a] = {};
            global_alias[a][b] = 1;
        for p in self.p:
            add_alias(p.path, p._id);
            if p.alias is not None:
                for a in p.alias:
                    add_alias(a, p._id);

        for k in global_alias.keys():
            k0 = global_alias[k].keys();
            if (len(k0) > 1):
                k1 = sorted(k0, key=lambda i:  len(self.p[i].remotes), reverse=True)
                dest = self.p[k1[0]]
                for i in (range(1,len(k1))):
                    f = self.p[k1[i]]
                    # merge f
                    f._ismerged = dest.path
                    print("Merge %s into %s" %(f.path,dest.path))
                    for v in (f.remotes):
                        for u in v['urls']:
                            dest.addremote(v['v'],u['url'], u['n'],mergefrom=f.path);
                    dest.addalias(f.path);
                    if (f.alias is not None):
                        for a in (f.alias):
                            dest.addalias(a);





        pass



# via repo:
class manifest(object):
    
    def __init__(self, args, fn):
        self.args = args
        self.fn = fn;
        self.doc = None
        self.tree = ftomanifest(args, fn, None, depth=0)
        self.m = self.flatten()
        self.extra_remotes = []

    def add_remote(self,r):
        self.extra_remotes.append(r)

    def flatten(self):
        p = projar(self,self.args)
        def touchproj(e):
            if isinstance(e,mh_project):
                p.add(e)
            elif isinstance(e,mh_remove_project):
                p.rem(e)
        self.traverse(['elem'], lambda x: touchproj(x))
        return p
    
    def traverse(self,tags,fn):
        a = [] + self.tree
        while len(a):
            e = a.pop(0)
            if hasattr(e, '_c'):
                a = e._c + a #retain order 
            if (e.match(tags)):
                fn(e)

    def get_projar(self):
        p = projar(None,self.args)
        nstack = [{}]

        def searchup(n):
            for h in nstack:
                if (not(n is None)) and (n in h):
                    return h[n]
                elif ('__default__' in h):
                    #print(h['__default__'])
                    return h[h['__default__']]
            return None

        # traverse over elements and process remove-project and project
        def touchproj(e):
            if isinstance(e,mh_project):
                p.add(e)
                remote = None
                try:
                    remote = e.remote
                except:
                    pass
                v = searchup(remote);
                e.xml.attrib['_gitserver_'] = v
            elif isinstance(e,mh_remove_project):
                p.rem(e)
            elif isinstance(e,mh_remote):
                #print(e.get_xml().decode("utf-8"))
                nstack[0][e.name] = e.fetch
            elif isinstance(e,mh_default):
                #print(e.get_xml().decode("utf-8"))
                nstack[0]['__default__'] = e.remote
            elif isinstance(e,mh_scope):
                if e.direction == "enter":
                    nstack.append({});
                elif e.direction == "exit":
                    nstack.pop();

        self.traverse(['elem'], lambda x: touchproj(x))
        return p

    def write(self, fn):
        with open(fn,"w") as f:
            f.write("""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<manifest>   
""");
            class ctx():
                def __init__(self):
                    self.a = [];
                    self.r = [];
                def addproject(self, e):
                    self.a.append(e)
                def remproject(self, e):
                    self.a = [ p for p in self.a if not (p.name ==  e.name) ]
                def addremote(self, e):
                    self.r.append(e)
            
            c = ctx()
            def add_elem(e):
                if isinstance(e,mh_project):
                    #print("Add "+e.name)
                    c.addproject(e)
                elif isinstance(e,mh_remove_project):
                    #print("Remove "+e.name)
                    c.remproject(e)
            self.traverse(['elem'], lambda x: add_elem(x))
            def add_remote(e):
                c.addremote(e)
            self.traverse(['remote','default'], lambda x: add_remote(x))

            if self.args.pathasname:
                f.write("""
 <remote name="origin" fetch="ssh://localhost:29418" />
 <default remote="origin" sync-c="true" sync-j="5"/>

""");
            else:
                for e in (self.extra_remotes+c.r):
                    f.write(" " + e.get_xml().decode("utf-8")+"\n");
            for e in c.a: #sorted(c.a, key=lambda x: x.name):
                if e.path == None:
                    e.path = e.name
                    if self.args.addmissingpath:
                        e.addnew = 1
                    e.setxml('path',e.name)
                else:
                    #print (e.path)
                    if self.args.pathasname:
                        e.setxml('name',e.path)
                f.write(" " + e.get_xml().decode("utf-8")+"\n");

            f.write("</manifest>\n");
