#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ast_compile import *
import os
import time

def main(args):    
    if len(args) < 2:
        print ("Usage: python3 main.py file_name.json")
        return
        
    file_ = args[1]
    cprint (text_colors.OKGREEN, file_ )
    jgraph    = json.load( open(file_, "r") )

    for i in jgraph["functions"]:
        parse_node(i)

    for name, f in functions.items():
        f.eval()

    file_name        = file_.split("/")[-1]
    output_file_name = os.getcwd() + "/output/" + file_name + ".ll"
    if not os.path.isdir('output'):
        os.mkdir("output")
    cprint (text_colors.OKBLUE, "writing to {}".format (output_file_name) )
    open(output_file_name, "w").write(str(module))
    
    return 0

if __name__ == '__main__':
    import sys
    start_time = time.time()
    retval = main(sys.argv)
    elapsed_time = round(time.time() - start_time,7)
    
    cprint( text_colors.OKCYAN, "done in {}s".format( elapsed_time ) )
    sys.exit(retval)
