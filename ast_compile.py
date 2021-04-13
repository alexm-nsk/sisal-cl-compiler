#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ast_compile.py
#
# This module contains functions to compile an IR provided by sisal-cl to an LLVM module
# Use parse_node function to transform an IR node into a Node (see the class below)
# Then call eval(...) on that Node to emit the corresponding code into the module

import json
from color_print import *
from codegen import *

# functions index as nodes
functions      = {}
# functions index as llvm objects
llvm_functions = {}
# all nodes index
nodes          = {}
# Edges Index:
edges_to       = {}
edges_from     = {}

#-----------------------------------------------------------

def clear_indexing_data():
    functions      = {}
    llvm_functions = {}
    nodes          = {}
    edges_to       = {}
    edges_from     = {}

#-----------------------------------------------------------

def nodes_pointing_at(node_id):
    if node_id not in edges_to:
        return []

    edges_pointing_at_node     = edges_to[node_id]
    nodes_pointing_at_the_node = [
                                    nodes[edge.src_node_id]
                                    for edge in edges_pointing_at_node
                                 ]

    return nodes_pointing_at_the_node

#-----------------------------------------------------------

def check_eval(function):
    def check(self, builder, vars_):
        if not self.output:
            self.output = []
        else:
            return self.output
        function(self, builder, vars_)
        return self.output
    return check

#-----------------------------------------------------------

class Node:

    def __init__(self, id_ = None):
        self.id    = id_
        self.edges = {}

    def eval(self, builder, vars_):
        cprint(bcolors.FAIL, "This should not be called!")
        pass

#-----------------------------------------------------------

class If(Node):

    def __init__(self, then, else_, condition):

        self.then      = then
        self.else_     = else_
        self.condition = condition

    @check_eval
    def eval(self, builder, vars_):

        #evaluate condition
        result = builder.alloca(ir.IntType(32))
        cond   = self.condition.eval(builder, vars_)[0]
        with builder.if_else(cond) as (then, otherwise):
            with then:
                builder.store(
                                self.then.eval( builder, vars_)[0],
                                result
                             )
            with otherwise:
                builder.store(
                                self.else_.eval(builder, vars_)[0],
                                result
                             )

        self.output = [builder.load(result)]

#-----------------------------------------------------------

class Condition(Node):

    def __init__(self):
        pass

    @check_eval
    def eval(self, builder, vars_):
        # find node pointing to condition's output:
        node, = nodes_pointing_at(self.id)

        self.output = node.eval(builder, vars_)

#-----------------------------------------------------------

class Branch(Node):

    def __init__(self):
        pass

    @check_eval
    def eval(self, builder, vars_):

        if not self.nodes:
            parents = nodes_pointing_at(self.id).remove(self)
           
            if not parents:
                self.output = [v["llvm_identifier"] for v in vars_]

        else:
            # get the node pointing at this node
            # TODO there can be many of these!
            result_node, = nodes_pointing_at(self.id)

            self.output = result_node.eval(builder, vars_)

#-----------------------------------------------------------

class Binary(Node):

    def __init__(self, operator):
        self.operator  = operator

    def __str__(self):
        return "Binary - '{}'".format(self.operator)

    @check_eval
    def eval(self, builder, vars_):

        #find node pointing to condition's output:
        #here we should get two edges pointing at this binary operation
        left_edge, right_edge = edges_to[ self.id ]
        left_node             = nodes[left_edge.src_node_id]
        right_node            = nodes[right_edge.src_node_id]
        
        # not all nodes send data to child nodes via edges, so we use this 
        # function to determine where should our bin-op node get that input data
        def select_source(edge):
            
            operand_node    = nodes[edge.src_node_id]
            node_type       = type(operand_node)
            types_with_args = [If, Function, Condition, Branch]
            
            if node_type in types_with_args:
                operand = vars_[edge.src_index]["llvm_identifier"]
            else:
                operand = operand_node.eval(builder, vars_)[0]
            return operand
            
        left  = select_source(left_edge)
        right = select_source(right_edge)
        
        if   self.operator == "<":
            self.output = [builder.icmp_signed("<", left , right, name='')]
        elif self.operator == "+":
            self.output = [builder.add             (left , right, name='')]
        elif self.operator == "-":
            self.output = [builder.sub             (left , right, name='')]
        else:
            raise Exception ("Unknown operator: {}". format (self.operator))

#-----------------------------------------------------------

class Literal(Node):

    def __init__(self, value):
        self.value  = value

    def __str__(self):
        return "Literal - '{}'".format(self.value)

    @check_eval
    def eval(self, builder, vars_):
        self.output = [ir.Constant(int32,self.value)]

#-----------------------------------------------------------

class Port(Node):

    def __init__(self):
        pass

#-----------------------------------------------------------

class FunctionCall(Node):

    def __init__(self, callee):
        self.callee  = callee

    @check_eval
    def eval(self, builder, vars_):
        
        parents = nodes_pointing_at (self.id)
        if type(parents[0]) == Function:
            self.output = [
                builder.call(
                    llvm_functions[self.callee],
                    (v["llvm_identifier"] for v in vars_) )
            ]
        else:
            # TODO make sure the order is correct using indices of edges
            self.output = [
                builder.call(
                    llvm_functions[self.callee],
                    (v.eval(builder, vars_)[0] for v in parents) )
            ]
            
#-----------------------------------------------------------

class Function(Node):

    def __init__(self, function_name, params, num_return_vals):
        self.function_name        = function_name
        self.edges                = {}
        self.num_return_vals      = num_return_vals
        # TODO: map types here instead of using int32 in all cases
        args                      = (int32 for p in params)
                                                    #   count output ports and types
                                                    #   here 
                                                    #     🠗
        if( num_return_vals > 1):
            function_type         = ir.FunctionType(ir.PointerType(ir.IntType(32)),args, False)
        else:
            function_type         = ir.FunctionType(ir.IntType(32), args, False)
            
        self.function                  = ir.Function(module, function_type, name=self.function_name)
        llvm_functions[function_name]  = self.function

    def eval(self):

        block = self.function.append_basic_block(name = "entry")

        # vars_ is a map that connects LLVM identifiers with SISAL names
        vars_ = []

        #put names for each parameter into our function definition in our module
        for n,p in enumerate(self.params):
            self.function.args[n].name = p["name"]
            # vars_ is a map that connects LLVM identifiers with SISAL names
            vars_.append({"name": p["name"], "llvm_identifier" : self.function.args[n]})
            # set values to the node's output so that it can be read anytime by it's child nodes
            self.output.append( self.function.args[n] )

        builder = ir.IRBuilder(block)

        # needed for printf:
        if self.function_name == "main":
            fmt_arg = add_bitcaster(builder)

        #---------------------------------------------------------------------------------
        # evaluate function's body:
        #---------------------------------------------------------------------------------

        out_edges = edges_to[self.id]
        results = []
        
        # TODO Make an array here and return it in the end
        # also change function return type to array or pointer
        if self.num_return_vals > 1:
            results_array = builder.alloca(int32, self.num_return_vals, "results")
        else:
            results_array = builder.alloca(int32, name = "result")
        for edge in out_edges:
            node = nodes[ edge.src_node_id ]
            results.append ( node.eval(builder, vars_)[0] )
        
        # add instructions to store function's results into allocated array
        # we then return the pointer to that array
        
        builder.store(results[0], results_array)
        for i in results[1:]:
            builder.store(i, builder.gep(results_array,[ir.Constant(int32,1)]))

        # put a label for the function's exit
        exit_ = self.function.append_basic_block(name = "exit")
        builder.branch(exit_)

        # print out the results in 'main'
        if self.function_name == "main":
            with builder.goto_block(exit_):
                for i in results:
                    builder.call(printf, [fmt_arg, i])

        with builder.goto_block(exit_):
            builder = builder.ret(results_array)

#-----------------------------------------------------------

class Edge:
    def __init__(self, src_node_id, dst_node_id, src_index , dst_index, src_type, dst_type = None):
        self.src_node_id = src_node_id
        if not dst_type:
            self.src_node_id = src_node_id
        else:
            self.dst_node_id = dst_node_id

        self.src_index = src_index
        self.dst_index = dst_index

        self.src_type  = src_type
        self.dst_type  = dst_type

        if not dst_node_id in edges_to:
            edges_to[dst_node_id] = []

        if not src_node_id in edges_from:
            edges_from[src_node_id] = []

        edges_to  [dst_node_id].append(self)
        edges_from[src_node_id].append(self)

    def __str__(self):
        return "<{} -> {}>".format(self.src_node_id, self.dst_node_id)

#----------------------------------------------------------------------------------------

def parse_params(nodes):

    io = [{
                    "name"    : f[0],
                    "node_id" : f[1]["nodeId"],
                    "type"    : f[1]["type"]["name"],
                    "index"   : f[1]["index"]
                } for f in nodes]
    return io

#------------------------------------------

def parse_io_nodes(nodes):

    return [{
                    "type" : f["type"]["name"],
                    "index": f["index"]
                } for f in nodes]

#----------------------------------------------------------------------------------------
# TODO use 'super' and constructor arguments instead of directly accessing fields
# TODO use getter, setter and property decorators on the base class to comply with OOP
#----------------------------------------------------------------------------------------

def parse_node(data):
     # parse parameters if they are provided
    if ("params" in data):
        params = parse_params   ( data ["params"]   )
    else:
        params = None

    # separate functions from other nodes:
    if "functionName" in data:
        num_ret_vals                        = len( data ["outPorts"] )
        new_node                            = Function( data[ "functionName" ], params, num_ret_vals )
        functions[ data[ "functionName" ] ] = new_node

    else:
        # find out what type of node we are parsing and use an appropriate initialization:
        if data ["name"] == "If":
            then = parse_node(data["branches"][0])

            if len(data["branches"]) > 0:
                else_ = parse_node(data["branches"][1])

            condition  = parse_node( data["condition"] )
            new_node   = If( then, else_, condition )

        elif data ["name"] == "Condition":
            new_node = Condition(  )

        elif data ["name"] == "Then" or data ["name"] == "Else":
            new_node = Branch(  )

        elif data ["name"] == "Binary":
            new_node = Binary( data["operator"] )

        elif data ["name"] == "FunctionCall":
            new_node = FunctionCall( data["callee"] )

        elif data ["name"] == "Literal":
            new_node = Literal( data["value"] )

        else:
            new_node = Node()

    new_node.id     = data["id"]
    new_node.params = params
    new_node.output = []
    
    # parse ports of a node
    new_node.input_ports         = parse_io_nodes ( data ["inPorts"]  )
    new_node.output_ports        = parse_io_nodes ( data ["outPorts"] )

    # parse subnodes of a node
    # an 'If' wouldn't have those, they are parsed previously in this function
    if "nodes" in data:
        new_node.nodes           = [ parse_node(n) for n in data["nodes"] ]

    # parse node's edges:
    # TODO maybe replace node name to the object's link
    if "edges" in data:   # edges list is present in node description
        if data["edges"]: # and it is not empty
            new_node.edges = [
                Edge( edge[0]["nodeId"], edge[1]["nodeId"],
                      edge[0]["index"] , edge[1]["index"],
                      edge[0]["type"]  , edge[1]["type"] )
                    for edge in data["edges"]
            ]

    # save a reference to this node in the 'nodes' global array:
    nodes[ new_node.id ] = new_node
    return new_node

#----------------------------------------------------------------------------------------
