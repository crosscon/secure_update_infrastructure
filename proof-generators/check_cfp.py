# Proof generator for control flow preservation properties
#
# Copyright 2024-2025 Alberto Tacchella <alberto.tacchella@unitn.it>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import subprocess
import networkx
import angr


__progname__ = 'check_cfp'
__version__ = '1.0'
default_output_filename = 'proof.cpc'
stage1_filename = 'stage1.smt'
stage2_filename = 'stage2.smt'


# Available security properties, first one is used as a default
props = ['cfp', 'cfr', 'cfiso']

def create_argument_parser():
    prop_string = 'Available security properties are:\n' + ' '.join(props) + '\n'

    parser = argparse.ArgumentParser(
        prog=__progname__,
        description='Generate a proof certificate for supported properties',
        epilog=prop_string)
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('original', type=argparse.FileType('rb'),
                        help='The binary file containing the original firmware image')
    parser.add_argument('updated', type=argparse.FileType('rb'),
                        help='The binary file containing the updated firmware image')
    parser.add_argument('-o', metavar='FILENAME',
                        type=argparse.FileType('w', encoding="utf-8"),
                        default=default_output_filename,
                        help='The name of the output file containing the proof (default: %(default)s)')
    parser.add_argument('-p', metavar='PROPERTY',
                        choices=props,
                        default=props[0],
                        help='Select the security property of interest (default: %(default)s)')
    parser.add_argument('-s', metavar='SYMBOL',
                        default="main",
                        help='Symbol from where to start the CFG reconstruction (default: %(default)s)')
    parser.add_argument('-t', metavar='SEC',
                        default="3600",
                        help='Timeout (in seconds) for cvc5 subprocesses (default: %(default)s)')
    parser.add_argument('-m', metavar=('SYM1', 'SYM2'),
                        action='append',
                        nargs=2,
                        help='Add a matching between symbols SYM1 and SYM2')
    parser.add_argument('-x',
                        default=False,
                        action='store_true',
                        help='Skip the proof generation phase')
    parser.add_argument('-k',
                        default=False,
                        action='store_true',
                        help='Keep the temporary SMT files')

    return parser


def recover_cfg(filename, start):
    p = angr.Project(filename, auto_load_libs = False);

    # Try to find the given symbol, to start CFG recovery from there;
    # otherwise use ELF entry point
    start_symbol = p.loader.find_symbol(start)
    if start_symbol != None:
        start_addr = start_symbol.rebased_addr
    else:
        print("Symbol", start, "not found, starting from binary entry point")
        start_addr = p.entry

    # Recover CFG using dynamic analysis
    cfg = p.analyses.CFGEmulated(
        keep_state = True,
        context_sensitivity_level = 0,
        starts = [start_addr])

    # Consider only the connected component of main
    if networkx.number_weakly_connected_components(cfg.graph) > 1:
        print("CFG is not weakly connected, aborting")
        exit(1)

    return cfg.graph

def get_node_name(n):
    if n.name == None:
        return "None" + str(n.addr)
    else:
        return n.name

def get_unique_nodes(cfg):
    node_dict = dict()
    for x in cfg.nodes():
        name = get_node_name(x)
        # ignore PathTerminators
        if name != "PathTerminator":
            if name not in node_dict:
                # name is unknown, add it to the dict
                node_dict[name] = x.addr
            elif node_dict[name] != x.addr:
                # name is known but with another address; add a new copy of node
                new_name = x.name + '_' + str(x.addr)
                node_dict[new_name] = x.addr
    return node_dict

def get_unique_edges(cfg, nodes):
    unique_edge_list = []
    # here we are supposing angr never generates different names with
    # the same address
    addr_dict = dict((v, k) for k, v in nodes.items())
    for x in cfg.edges():
        src = addr_dict[x[0].addr]
        trg = addr_dict[x[1].addr]
        # ignore PathTerminators
        if src != "PathTerminator" and trg != "PathTerminator":
            if (src, trg) not in unique_edge_list:
                unique_edge_list.append((src,trg))
    return unique_edge_list

def qualify(name, prefix):
    return prefix + '_' + name

def generate_vertex_decl(node_list, prefix):
    qualified_node_list = map(lambda s: qualify(s,prefix), node_list)
    formula = "(" + ") (".join(qualified_node_list) + ")"
    return formula

def generate_edges_decl(edge_list, prefix):
    formula = ""
    for e in edge_list:
        src = qualify(e[0],prefix)
        trg = qualify(e[1],prefix)
        formula += "(and (= x " + src + ") (= y " + trg + ")) "
    return formula
        
def generate_constraints(l1, l2, user_def):
    clist = []
    n = 0
    for name in filter(lambda s: '+' not in s, l1):
        if (name in l2) and (name[:4] != "None"):
            if (args.p == 'cfr'):
                clist.append("(= (f " + qualify(name,'V2') + ") " + qualify(name,'V1') + ")")
            else:
                clist.append("(= (f " + qualify(name,'V1') + ") " + qualify(name,'V2') + ")")
            n += 1
    print(n, "identifications found")

    # add user-defined constraints
    if user_def:
        for x in user_def:
            src = x[0]
            trg = x[1]
            if (args.p == 'cfr'):
                clist.append("(= (f " + qualify(src,'V2') + ") " + qualify(trg,'V1') + ")")
            else:
                clist.append("(= (f " + qualify(src,'V1') + ") " + qualify(trg,'V2') + ")")
    
    if clist:
        return "(and " + " ".join(clist) + ")"
    else:
        return ""

def surrender():
    print("Property does not hold, aborting")
    exit(1)


if __name__ == '__main__':
    p = create_argument_parser()
    args = p.parse_args()

    g1 = recover_cfg(args.original, args.s)
    g1_nodes = get_unique_nodes(g1)
    print("Number of unique names in G1:", len(g1_nodes))
    g1_edges = get_unique_edges(g1, g1_nodes)
    print("Number of unique edges in G1:", len(g1_edges))

    smt_v1_def = generate_vertex_decl(list(g1_nodes), 'V1')
    smt_e1_def = generate_edges_decl(g1_edges, 'V1')

    g2 = recover_cfg(args.updated, args.s)
    g2_nodes = get_unique_nodes(g2)
    print("Number of unique names in G2:", len(g2_nodes))
    g2_edges = get_unique_edges(g2, g2_nodes)
    print("Number of unique edges in G2:", len(g2_edges))

    smt_v2_def = generate_vertex_decl(list(g2_nodes), 'V2')
    smt_e2_def = generate_edges_decl(g2_edges, 'V2')

    # check necessary conditions
    if (args.p == 'cfp'):
        if (len(g2_nodes) < len(g1_nodes)) or (len(g2_edges) < len(g1_edges)):
            surrender()
    if (args.p == 'cfr'):
        if (len(g1_nodes) < len(g2_nodes)) or (len(g1_edges) < len(g2_edges)):
            surrender()
    if (args.p == 'cfiso'):
        if (len(g1_nodes) != len(g2_nodes)) or (len(g1_edges) != len(g2_edges)):
            surrender()

    # generate constraint for identifiable nodes
    smt_constr = generate_constraints(list(g1_nodes), list(g2_nodes), args.m)

    # select the SMT encoding of the required property
    if args.p == 'cfp':
        # graph 1 embeds into graph 2
        smt_f_def = "(declare-fun f (V1) V2)\n"
        smt_property = """
    (and (forall ((va V1) (vb V1))
                 (=> (g1 va vb) (g2 (f va) (f vb))))
         (forall ((va V1) (vb V1))
                 (=> (= (f va) (f vb)) (= va vb))))"""
    elif args.p == 'cfr':
        # graph 2 embeds into graph 1
        smt_f_def = "(declare-fun f (V2) V1)\n"
        smt_property = """
    (and (forall ((va V2) (vb V2))
                 (=> (g2 va vb) (g1 (f va) (f vb))))
         (forall ((va V2) (vb V2))
                 (=> (= (f va) (f vb)) (= va vb))))"""
    elif args.p == 'cfiso':
        # graph 1 is isomorphic to graph 2
        smt_f_def = "(declare-fun f (V1) V2)\n"
        smt_property = """
    (and (forall ((va V1) (vb V1))
                 (=> (g1 va vb) (g2 (f va) (f vb))))
         (forall ((va V1) (vb V1))
                 (=> (g2 (f va) (f vb)) (g1 va vb)))
         (forall ((va V1) (vb V1))
                 (=> (= (f va) (f vb)) (= va vb))))"""
    else:
        # this should never happen if argparse has done its job
        raise ValueError('unkown property ' + args.p)

    # write stage 1 smt file
    with open(stage1_filename, 'w', encoding="utf-8") as f:
        f.write('(set-logic UFDT)\n\n')
        f.write('(declare-datatype V1 (' + smt_v1_def + '))\n\n')
        f.write('(define-fun g1 ((x V1) (y V1)) Bool\n    (or ' + smt_e1_def + '))\n\n')
        f.write('(declare-datatype V2 (' + smt_v2_def + '))\n\n')
        f.write('(define-fun g2 ((x V2) (y V2)) Bool\n    (or ' + smt_e2_def + '))\n\n')
        f.write(smt_f_def)
        f.write('(assert\n    ' + smt_constr + ')\n')
        f.write('(assert' + smt_property + ')\n\n(check-sat)\n(get-model)\n')


    # call cvc5 to get a model for f
    res = subprocess.run(["cvc5",
                          "--finite-model-find",
                          "--no-cbqi",
                          "--produce-models",
                          "--tlimit=" + args.t + "000",
                          stage1_filename],
                         capture_output=True, text=True, encoding="utf-8")
    
    if res.returncode != 0:
        print("No output from cvc5, aborting. Error is:")
        print(res.stderr)
        exit(1)

    if not args.k:
        os.remove(stage1_filename)

    cvc5_out = res.stdout.split("\n")
    if cvc5_out[0] == "unsat":
        surrender()

    # WARNING: this way of recovering the model depends on the precise format of
    # cvc5's output and is very fragile!
    model = cvc5_out[2]

    if args.x:
        print(model)
        exit(0)
    else:
        print("Model found, generating proof")

    # write stage 2 smt file
    with open(stage2_filename, 'w', encoding="utf-8") as f:
        f.write('(set-logic UFDT)\n\n')
        f.write('(declare-datatype V1 (' + smt_v1_def + '))\n\n')
        f.write('(define-fun g1 ((x V1) (y V1)) Bool\n    (or ' + smt_e1_def + '))\n\n')
        f.write('(declare-datatype V2 (' + smt_v2_def + '))\n\n')
        f.write('(define-fun g2 ((x V2) (y V2)) Bool\n    (or ' + smt_e2_def + '))\n\n')
        f.write(model)
        f.write('\n(assert (not' + smt_property + '))\n\n(check-sat)\n')

    # call cvc5 to get the proof
    res = subprocess.run(["cvc5",
                          "--finite-model-find",
                          "--no-cbqi",
                          "--dump-proof",
                          "--proof-format-mode=cpc",
                          "--tlimit=" + args.t + "000",
                          stage2_filename],
                         capture_output=True, text=True, encoding="utf-8")

    if res.returncode != 0:
        print("No output from cvc5, aborting. Error is:")
        print(res.stderr)
        exit(1)

    cvc5_out = res.stdout.split("\n",1)
    if cvc5_out[0] == "sat":
        # this should never happen
        print("Something went horribly wrong, aborting")
        exit(1)
    else:
        print("cvc5 process finished successfully, writing proof")

    args.o.write('(include "./proofs/eo/cpc/Cpc.eo")\n')
    args.o.write(cvc5_out[1])

    if not args.k:
        os.remove(stage2_filename)


