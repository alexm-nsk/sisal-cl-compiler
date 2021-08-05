; ModuleID = "microsisal"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"printf"(i8* %".1", ...) 

define i32 @"Fib"(i32 %"M") 
{
entry:
  %"result" = alloca i32
  %".3" = alloca i32
  %".4" = icmp slt i32 %"M", 2
  br i1 %".4", label %"entry.if", label %"entry.else"
entry.if:
  store i32 %"M", i32* %".3"
  br label %"entry.endif"
entry.else:
  %".8" = sub i32 %"M", 1
  %".9" = call i32 @"Fib"(i32 %".8")
  %".10" = sub i32 %"M", 2
  %".11" = call i32 @"Fib"(i32 %".10")
  %".12" = add i32 %".9", %".11"
  store i32 %".12", i32* %".3"
  br label %"entry.endif"
entry.endif:
  %".15" = load i32, i32* %".3"
  store i32 %".15", i32* %"result"
  br label %"exit"
exit:
  ret i32* %"result"
}

define i32 @"main"() 
{
entry:
  %".2" = bitcast [5 x i8]* @"fstr" to i8*
  %"result" = alloca i32
  %".3" = call i32 @"Fib"(i32 12)
  store i32 %".3", i32* %"result"
  br label %"exit"
exit:
  %".6" = call i32 (i8*, ...) @"printf"(i8* %".2", i32 %".3")
  ret i32* %"result"
}

@"fstr" = internal constant [5 x i8] c"%i \0a\00"