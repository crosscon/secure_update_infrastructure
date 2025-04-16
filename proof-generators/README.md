# PROOF GENERATORS

This folder contains two Python scripts that can be used to generate proof
certificates for the following kind of behavioral properties:

* _Control flow preservation_ and _Control flow invariance_ (script `check_cfp.py`)
* _Binary instrumentation_ (script `check_instr.py`)

## Dependencies

The scripts have the following dependencies:

* the **angr** binary analysis framework (https://github.com/angr/angr) -- tested with version 9.2.117
* the **cvc5** SMT solver (https://github.com/cvc5/cvc5/) -- tested with version 1.2.1-dev
  
Python bindings for angr are needed (this may require setting up a virtual
environment). The cvc5 solver is called externally, so the only requisite is
that the cvc5 binary is available in the execution path.

## Running the scripts

Some basic usage information is available by running the scripts with the `-h`
flag. More detailed documentation will be included in the deliverable 3.3 of
the CROSSCON project.



