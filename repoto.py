#!/usr/bin/python3
import os, sys, re, argparse, json
from repo.manifest import manifest, mh_project, mh_remove_project, projar, multirepolist, multirepo
from repo.html import repohtml, diffdirhtml, initrchtml
from repo.initrc import flatparse
from repo.dirs import filesunder
from xml.etree.ElementTree import tostring
from json import dumps, loads, JSONEncoder, JSONDecoder
from pprint import pprint
import pickle, shutil
import pystache

class PythonObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (list, dict, str, unicode, int, float, bool, type(None))):
            return JSONEncoder.encode(self, obj)
        elif isinstance(obj, set):
            return JSONEncoder.encode(self, list(obj)) #str(obj) #"set([{}])".format(",".join([ PythonObjectEncoder.default(self,i) for i in list(obj)]))
        return pickle.dumps(obj)

def diffdir(args):
    filesundera = filesunder(args, args.dira);
    filesunderb = filesunder(args, args.dirb);
    filesundera.diff(filesunderb);
    j = diffdirhtml(args, filesundera);
    j.generate(args.output);

def listrepos(args):
    mar = []
    for fn in args.inputs:
        o0 = manifest(args, fn);
        p = projar(None,args)
        def touchproj(e):
            if isinstance(e,mh_project):
                p.add(e)
        o0.traverse(['elem'], lambda x: touchproj(x))
        projects = p.p
        a = []
        for p in projects:
            n = str(p)
            if args.verbose:
                print (p.name);
            e = { 'n' : p.name, 'sha' : p.revision , 'path' : p.path }
            if not (args.aosproot is None):
                d = os.popen('cd {}; git show-ref -d'.format(os.path.join(args.aosproot,p.path))).readlines()
                e['refs'] = d;
            a.append(e);
        mar.append({'fn':fn,
                    'projects':a});

    if (args.json):
        with open(args.json, "w") as f:
            j = json.dumps({'d':mar}, sort_keys=True, indent=4, separators=(',', ': '), cls=PythonObjectEncoder);
            f.write(j);

    if (args.html):
        j = repohtml(args, a);
        j.generate(args.output);


def flatinit(args):
    a = [flatparse(args, i) for i in args.inputs]
    j = initrchtml(args, a);
    j.generate(args.output);

def do_flatten(args,fin,fout):
    o0 = manifest(args, fin);
    p = projar(None,args)
    def touchproj(e):
        if isinstance(e,mh_project):
            p.add(e)
        elif isinstance(e,mh_remove_project):
            p.rem(e)
    o0.traverse(['elem'], lambda x: touchproj(x))
    projects = p.p
    if args.sort:
        projects = sorted(projects, key=lambda x: x.name)

    for p in projects:
        n = str(p)
        if not (args.removepath is None):
            n = n.replace(args.removepath,"")
        #print (" "+n);
    o0.write(fout)

def flatten(args):
    o0 = do_flatten(args, args.file, args.output);

def convbare(args):
    o0 = manifest(args, args.file);
    p = projar(None,args)
    def touchproj(e):
        if isinstance(e,mh_project):
            p.add(e)
        elif isinstance(e,mh_remove_project):
            p.rem(e)
    o0.traverse(['elem'], lambda x: touchproj(x))
    projects = p.p
    
    for p in projects:
        n = p.name
        pa = p.path
        if not (args.removepath is None):
            n = n.replace(args.removepath,"")
        if pa is None:
            pa = n
        print ("{} {}".format(n,pa));
    
def update(args):
    a0 = manifest(args, args.aosp);
    o0 = manifest(args, args.file);
    
    a0_p = a0.flatten()
    o0_p = o0.flatten()

    for p in a0_p.projects():
        if (o0_p.contain(p)):
            o0_p.updateshawith(p)
        else:
            o0_p.addproject(p)
    
    o0.write(args.output)

def filteraosp(args):
    a0 = manifest(args, args.aosp);
    o0 = manifest(args, args.file);
    
    a0_p = a0.flatten()
    o0_p = o0.flatten()
    
    aout = projar(None,args)
    
    for p in o0_p.projects():
        if (a0_p.contain(p)):
            aout.add(p)
    
    for p in aout.projects():
        sys.stdout.write(tostring(p.xml))
    
def diff(args):
    a0 = None
    if not (args.aosp is None):
        a0 = manifest(args, args.aosp);
        a0_p = a0.flatten()
    o0 = manifest(args, args.file1);
    target = manifest(args, args.file2);
    
    o0_p = o0.flatten()
    target_p = target.flatten()

    a_removed = projar(None,args)
    a_changed = projar(None,args)
    a_added   = projar(None,args)

    for p in target_p.projects():
        if (o0_p.contain(p)):
            if (o0_p.changed(p)):
                a_changed.add(p)
                f = o0_p.getProject(p)
                print ("change {}->{}:{}".format(f.revision,p.revision,p.name)) 
            else:
                pass
        else:
            a_added.addproject(p)
    
    for p in o0_p.projects():
        if not (target_p.contain(p)):
            a_removed.add(p)
            
    print ("Remove:");
    for p in a_removed.projects():
        print(" "+str(p))

    print ("Changed:");
    for p in a_changed.projects():
        print(" "+str(p))
        
    print ("Added:");
    for p in a_added.projects():
        print(" "+str(p))
    
    for p in a_changed.projects() + a_removed.projects():
        print( "<remove-project name=\"{}\"/>".format(p.name))
    for p in a_changed.projects() + a_added.projects():
        sys.stdout.write(tostring(p.xml))
    
def removed(args):
    o0 = manifest(args, args.file);
    o0_p = o0.flatten()
    
    p = projar(None,args)

    def searchremoved(e):
        if isinstance(e,mh_remove_project):
            p.rem(e)
            p.add(e)
    o0.traverse(['elem'], lambda x: searchremoved(x))
    projects = p.p
    removed_projects={}
    for p in projects:
        n = p.name
        if not (args.removepath is None):
            n = n.replace(args.removepath,"")
        removed_projects[n] = p
        print ( " + "+str(p))

    if not (args.aosp is None):
        print ("Removed aosp projects")
        a0 = manifest(args, args.aosp);
        a0_p = a0.flatten()
        for p in a0_p.projects():
            n = p.name
            a2 = [ e for e in o0_p.projects() if e.shortname(args) == n]
            if n in removed_projects:
                print ( " + aos-rev:{} ihu-rev:{} aosp/{} {}".format(p.revision,a2[0].revision,str(removed_projects[n]),p.path))
        
def parse(args):

    o0 = manifest(args, args.file);
    print("Elements:");
    def print_elem(e):
        print (" "+str(e));
    o0.traverse(['elem'], lambda x: print_elem(x))

    print("Hirarchies:");
    def print_hirarchy(e):
        print (" "+str(e));
    o0.traverse(['manifest'], lambda x: print_hirarchy(x))

    print("Removes:");
    def print_remove(e):
        print (" "+str(e));
    o0.traverse(['remove_project'], lambda x: print_remove(x))

def getaosp_projects(args):
    if (args.aosp is None):
        raise("--aosp required")
    a0 = manifest(args, args.aosp);
    a0_p = a0.flatten()
    return a0_p

    
def isaosp(args):
    a = getaosp_projects(args)
    n = args.repo
    found=0
    for p in a.projects():
        if p.nameorpath(args) == n:
            found=1
            break;
    if found:
        sys.stdout.write("yes");
    else:
        sys.stdout.write("no");
    

def getrev(args):
    a = getaosp_projects(args)
    n = args.repo
    found=0
    for p in a.projects():
        if p.nameorpath(args) == n:
            sys.stdout.write(p.revision)
            break;
    
def genmirrors(args):
    mp = multirepolist(args);
    for fn in args.inputs:
        fnbase=os.path.dirname(fn)
        with open(fn,"rb") as f:
            a = json.load(f)
            for m in a:
                for mfnh in m['manifests']:
                    mfn = os.path.join(fnbase,mfnh['n'])
                    if 'gitbase' in mfnh:
                        args.gitbase = mfnh['gitbase']
                    #if args.verbose:
                    print("+ Load {}:{}".format(m['vendor'],mfn));

                    m0 = manifest(args, mfn);
                    p0 = m0.get_projar();
                    # rewrite repository name if prefix matches
                    if "prefix" in m:
                        pl = len(m['prefix'])
                        for e in p0.p:
                            if e.name.startswith(m['prefix']):
                                on = e.name;
                                oserver = e.xml.attrib['_gitserver_']
                                n = on[pl:]
                                server = oserver
                                if not (server.endswith("/")):
                                    server = server + "/"
                                server = oserver + m['prefix']
                                if (server.endswith("/")):
                                    server = server[0:-1]
                                e.xml.attrib['_gitserver_'] = server
                                e.name = n
                                if args.verbose:
                                    print ("Rewrite {}+{} to {}+{}".format(oserver,on,e.xml.attrib['_gitserver_'],e.name))
                    for e in p0.p:
                        rpath=e.path
                        if rpath == "." or rpath == "./":
                            rpath = None
                        if rpath==None:
                            rpath = e.name
                        elif 'path-prefix' in m:
                            #print(m['path-prefix'])
                            if rpath.startswith(m['path-prefix']):
                                rpath = rpath[len(m['path-prefix']):]
                        p = mp.regProj(rpath);
                        if 'alias' in mfnh:
                            if p.alias is None:
                                p.alias = []
                            if mfnh['alias'] == 1:
                                #print ("%s n: %s " %(e.path,e.name))
                                if e.path != e.name:
                                        #print("!! overwrite previouse alias for {} : {} !!".format(e.name, p.alias))
                                    if e.name not in p.alias:
                                        p.alias.append(e.name)
                            else:
                                _a = mfnh['alias']
                                _p = re.compile('\$\{name\}')
                                if e.name is not None:
                                    _a = _p.sub(e.name, _a);
                                _p = re.compile('\$\{path\}')
                                if e.path is not None:
                                    _a = _p.sub(e.path, _a);
                                if _a not in p.alias:
                                    p.alias.append(_a)

                        p.addremote(m['vendor'], e.xml.attrib['_gitserver_'], e.name);
                    if 'manifest-repo' in mfnh:
                        mfr = mfnh['manifest-repo']
                        p = mp.regProj(mfr['path']);
                        p.addremote(m['vendor'], mfr['url'], mfr['name']);
                        if ('alias' in mfr) and (_mfr['alias'] not in p.alias):
                            p.alias.append(mfr['alias'])

            # rewrite manifest
            for m in a:
                for mfnh in m['manifests']:
                    mfn = os.path.join(fnbase,mfnh['n'])
                    mfnbase = os.path.basename(mfnh['n'])
                    if 'gitbase' in mfnh:
                        args.gitbase = mfnh['gitbase']
                    if args.verbose:
                        print("+ Load {}:{}".format(m['vendor'],mfn));
                    if args.flattenrepo:
                        if 'flattened-suffix' in mfnh:
                            mfnbase = mfnbase+mfnh['flattened-suffix']
                        do_flatten(args, mfn, os.path.join(args.flattenrepo,mfnbase+".flatten.xml"));

    mp.merge();

    if args.clonescript:
        dstbase=os.path.join(os.path.dirname(args.clonescript),"base.sh")
        if not os.path.exists(dstbase):
            shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)),"repo/base.sh"),dstbase)
        with open(args.clonescript,"w") as f:
            f.write(mp.clonescript());
        with open(args.clonescript+".json","w") as f:
            f.write(mp.jsonscript());

def main():

    parser = argparse.ArgumentParser(prog='repoto')
    parser.add_argument('--verbose', action='store_true', help='verbose')
    parser.add_argument('--log', type=str, default=None, help='logfile')
    parser.add_argument('--sort', '-x', action='count')
    parser.add_argument('--remove-path', '-r', dest='removepath', default=None)
    parser.add_argument('--aosp', '-a', dest='aosp', default=None)
    subparsers = parser.add_subparsers(help='sub-commands help')
    
    # create the parser for the "flatten" command
    parser_a = subparsers.add_parser('flatten', help='flatten and sort projects')
    parser_a.add_argument('--sort', '-x', action='count')
    parser_a.add_argument('--pathasname', '-n', action='count', default=0)
    parser_a.add_argument('--addmissingpath', '-m', action='count', default=0)
    parser_a.add_argument('--remove-path', '-r', dest='removepath', default=None)
    parser_a.add_argument('file', type=str, help='root maifest')
    parser_a.add_argument('output', type=str, help='flattend output')
    parser_a.set_defaults(func=flatten)

    # create the parser for the "update" command
    parser_b = subparsers.add_parser('update', help='update shas')
    parser_b.add_argument('--defserver', '-A', dest='defserver', default=None)
    parser_b.add_argument('file', type=str, help='root maifest')
    parser_b.add_argument('output', type=str, help='flattend output')
    parser_b.set_defaults(func=update)

    # "removed" command
    parser_c = subparsers.add_parser('removed', help='list removed aosp projects')
    parser_c.add_argument('--defserver', '-A', dest='defserver', default=None)
    parser_c.add_argument('--aosp', '-a', dest='aosp', default=None)
    parser_c.add_argument('file', type=str, help='root maifest')
    parser_c.set_defaults(func=removed)

    # convert repo sync tree to bare repos
    parser_d = subparsers.add_parser('convbare', help='convert')
    parser_d.add_argument('file', type=str, help='root maifest')
    parser_d.set_defaults(func=convbare)
    
    # create the parser for the "parse" command
    parser_e = subparsers.add_parser('parse', help='parse and print info on projects')
    parser_e.add_argument('file', type=str, help='root manifest')
    parser_e.set_defaults(func=parse)

    # "diff" command
    parser_f = subparsers.add_parser('diff', help='diff projects')
    parser_f.add_argument('--defserver', '-A', dest='defserver', default=None)
    parser_f.add_argument('file1', type=str, help='root maifest 1')
    parser_f.add_argument('file2', type=str, help='root maifest 2')
    parser_f.set_defaults(func=diff)

    # "isaosp" command
    parser_g = subparsers.add_parser('isaosp', help='is aosp repo')
    parser_g.add_argument('repo', type=str, help='repo')
    parser_g.set_defaults(func=isaosp)

    # "getrev" command
    parser_g = subparsers.add_parser('getrev', help='getrev repo')
    parser_g.add_argument('repo', type=str, help='repo')
    parser_g.set_defaults(func=getrev)

    # "getrev" command
    parser_h = subparsers.add_parser('filter', help='filter aosp')
    parser_h.add_argument('file', type=str, help='repo')
    parser_h.set_defaults(func=filteraosp)
    
    # create the parser for the "flatten" command
    parser_list = subparsers.add_parser('list', help='list repos')
    parser_list.add_argument('--json', '-j', dest='json', type=str)
    parser_list.add_argument('--html', dest='html', action='store_true')
    parser_list.add_argument('--aosproot', '-a', dest='aosproot', default=None, type=str)
    parser_list.add_argument('--output', '-o', type=str, help='output')
    parser_list.add_argument('inputs', nargs='*', default=[], help='input list')
    parser_list.set_defaults(func=listrepos)

    # create the parser for the "flatten" command
    parser_dd = subparsers.add_parser('dirdiff', help='diff output folders')
    parser_dd.add_argument('--json', '-j', dest='json', action='store_true')
    parser_dd.add_argument('--maxdiff', '-m', dest='maxdiff', type=int, default=10000)
    parser_dd.add_argument('dira', type=str, help='dir a')
    parser_dd.add_argument('dirb', type=str, help='dir b')
    parser_dd.add_argument('output', type=str, help='output')
    parser_dd.set_defaults(func=diffdir)

    # create the parser for the "flatint" command
    parser_fi = subparsers.add_parser('flatinit', help='parse init files')
    parser_fi.add_argument('--output', '-o', type=str, help='output', default=None)
    parser_fi.add_argument('inputs', nargs='*', default=[], help='output')
    parser_fi.set_defaults(func=flatinit)

    # create the parser for the "genmirrors" command
    parser_genm = subparsers.add_parser('genmirrors', help='genmirrors')
    parser_genm.add_argument('--addmissingpath', '-m', action='count', default=1)
    parser_genm.add_argument('--pathasname', '-n', action='count', default=1)
    parser_genm.add_argument('--clonescript', '-o', type=str, help='clonescript', default=None)
    parser_genm.add_argument('--flattenrepo', '-f', type=str, help='flattenrepo', default=None)
    parser_genm.add_argument('inputs', nargs='*', default=[], help='input')
    parser_genm.set_defaults(func=genmirrors)


    opt = parser.parse_args()
    opt.func(opt)

if __name__ == "__main__":
    main()
    
