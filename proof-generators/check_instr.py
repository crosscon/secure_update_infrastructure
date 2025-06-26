# Proof generator for binary instrumentation checking
#
# Copyright 2024-2025 Alberto Tacchella <alberto.tacchella@unitn.it>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import subprocess
import networkx
import angr


__progname__ = 'check_instr'
__version__ = '1.0'
default_output_filename = 'proof.cpc'
temp_filename = 'temp.smt'

def create_argument_parser():
    parser = argparse.ArgumentParser(
        prog=__progname__,
        description='Generate a proof certificate for binary instrumentation')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('filename', type=argparse.FileType('rb'),
                        help='The binary file to check')
    parser.add_argument('-o', metavar='FILENAME',
                        type=argparse.FileType('w', encoding="utf-8"),
                        default=default_output_filename,
                        help='The name of the output file containing the proof (default: %(default)s)')
    parser.add_argument('-s', metavar='SYMBOL',
                        default="main",
                        help='Name of function to analyze (default: %(default)s)')
    parser.add_argument('-t', metavar='SEC',
                        default="3600",
                        help='Timeout (in seconds) for cvc5 subprocesses (default: %(default)s)')
    parser.add_argument('-x', metavar='REGEXP',
                        required=True,
                        help='Regular expression to exclude on the disassembled code')
    parser.add_argument('-k',
                        default=False,
                        action='store_true',
                        help='Keep the temporary SMT file')

    return parser

def disassemble(filename, symbol):
    p = angr.Project(filename, auto_load_libs = False);

    cfg = p.analyses.CFGFast(normalize=True)
    listing = []

    if symbol:
        maybe_fun = [x for x in cfg.kb.functions.get_by_name(symbol)]
        if maybe_fun:
            if len(maybe_fun) == 1:
                ins_count = 0
                funblocks = maybe_fun[0].blocks
                for blk in funblocks:
                    ins_list = blk.disassembly.insns
                    for ins in ins_list:
                        # f"{ins.address:#x}:\t{ins.mnemonic}\t{ins.op_str}"
                        source = f"{ins.mnemonic} {ins.op_str}"
                        listing.append(source)
                        ins_count += 1
                return ('|'.join(listing), ins_count)
            else:
                print("Name is ambiguous")
                return None
        else:
            print("Name not found")
            return None
    else:
        ins_count = 0
        for node in sorted(cfg.model.nodes(), key = lambda n: n.addr):
            if not node.is_simprocedure:
                ins_list = node.block.disassembly.insns
                for ins in ins_list:
                    # f"{ins.address:#x}:\t{ins.mnemonic}\t{ins.op_str}"
                    source = f"{ins.mnemonic} {ins.op_str}"
                    listing.append(source)
                    ins_count += 1
        return ('|'.join(listing), ins_count)

    
def surrender():
    print("Property does not hold, aborting")
    exit(1)


if __name__ == '__main__':
    p = create_argument_parser()
    args = p.parse_args()

    res = disassemble(args.filename, args.s)
    if not res:
        print("Could not disassemble the binary, aborting")
        exit(1)

    (listing, ins_count) = res

    regex_hex_constant = """
(define-const R_hex RegLan
  (re.++ (str.to_re "0") (re.union (str.to_re "x")
                                   (str.to_re "X"))
         (re.+ (re.union (re.range "0" "9")
                         (re.range "a" "f")
                         (re.range "A" "F"))))
    """

    regex_x86_64_register = """
(define-const R_reg RegLan
  (re.union
    (re.++ (str.to_re "r") (re.range "b" "d") (str.to_re "x"))
    (re.++ (str.to_re "r") (re.union (str.to_re "s") (str.to_re "d")) (str.to_re "i"))
    (re.++ (str.to_re "r") (re.union (str.to_re "s") (str.to_re "b")) (str.to_re "p"))
    (re.++ (str.to_re "r") (re.union (str.to_re "8") (str.to_re "9")))
    (re.++ (str.to_re "r1") (re.range "0" "5"))))
    """

    with open(temp_filename, 'w', encoding="utf-8") as f:
        f.write('(set-logic QF_SLIA)\n\n')
        f.write('(define-const code String "')
        f.write(listing)
        f.write('")\n\n')
        f.write('(declare-const x String)\n(declare-const y String)\n')
        f.write(regex_x86_64_register)
        if args.x:
            # Exclude pattern
            f.write('\n(define-const R RegLan ')
            f.write(args.x)
            f.write(')\n\n(assert (str.in_re code (re.++ (str.to_re x) R (str.to_re y))))\n\n')
        #
        # Add other templates here...
        #
        f.write('(check-sat)\n')

    # call cvc5
    res = subprocess.run(["cvc5",
                          "--dump-proof",
                          "--proof-format-mode=cpc",
                          "--tlimit=" + args.t + "000",
                          temp_filename],
                         capture_output=True, text=True, encoding="utf-8")

    if res.returncode != 0:
        print("No output from cvc5, aborting. Error is:")
        print(res.stderr)
        exit(1)

    if not args.k:
        os.remove(temp_filename)


    cvc5_out = res.stdout.split("\n",1)
    if cvc5_out[0] == "sat":
        print("Property does not hold, aborting")
        exit(1)
    else:
        print("cvc5 process finished successfully, writing proof")

    args.o.write('(include "./proofs/eo/cpc/Cpc.eo")\n')
    args.o.write(cvc5_out[1])

    print("Instruction count:", ins_count, " Listing size:", len(listing))
