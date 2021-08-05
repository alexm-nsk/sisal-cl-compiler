; ModuleID = "microsisal"
target triple = "x86_64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"printf"(i8* %".1", ...) 

define i32* @"foo"(i32 %"a", i32 %"b", i32 %"c") 
{
entry:
  %"results" = alloca i32, i32 2
  %".5" = add i32 %"a", %"b"
  %".6" = add i32 %".5", %"c"
  %".7" = sub i32 %"a", %"b"
  %".8" = sub i32 %".7", %"c"
  store i32 %".6", i32* %"results"
  %".10" = getelementptr i32, i32* %"results", i32 1
  store i32 %".8", i32* %".10"
  br label %"exit"
exit:
  ret i32* %"results"
}
