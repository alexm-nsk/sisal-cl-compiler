from llvmlite import ir, binding

binding.initialize()
binding.initialize_native_target()
binding.initialize_all_asmprinters()

module        = ir.Module(name = "microsisal")
module.triple = binding.get_default_triple()

int32 = ir.IntType(32)

if True:
    target         = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod    = binding.parse_assembly("")
    engine         = binding.create_mcjit_compiler(backing_mod, target_machine)

#initialize printf

voidptr_ty     = ir.IntType(8).as_pointer()
printf_ty      = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg = True)
printf         = ir.Function(module, printf_ty, name = "printf")

def add_bitcaster(builder):
    voidptr_ty                 = ir.IntType(8).as_pointer()
    fmt = "%i \n\0"

    c_fmt                      = ir.Constant(ir.ArrayType(ir.IntType(8),len(fmt)), bytearray(fmt.encode("utf8")))
    global_fmt                 = ir.GlobalVariable(module, c_fmt.type, name = "fstr")
    global_fmt.linkage         = "internal"
    global_fmt.global_constant = True
    global_fmt.initializer     = c_fmt
    fmt_arg                    = builder.bitcast(global_fmt, voidptr_ty)
    return fmt_arg


if __name__ == "__main__":
    pass
