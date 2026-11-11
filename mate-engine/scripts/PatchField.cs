using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// PatchField.exe <in.dll> <out.dll> <FIELD_NAME> <VALUE>
// 找出 AvatarAnimatorController..ctor 中的 "<ldc>; stfld <FIELD_NAME>"
// 把 ldc 換成 ldc.i4.s <VALUE>。原本 ldc.i4.5 只有 1 byte、ldc.i4.s 為 2 byte，
// 差額交給 Cecil 重寫 IL 處理；不要手工插 byte（會讓 .text 之後所有 method RVA 錯位）。

class PatchField
{
    static bool IsLdcI4(Code c)
    {
        return c == Code.Ldc_I4_M1 || c == Code.Ldc_I4_0 || c == Code.Ldc_I4_1 ||
               c == Code.Ldc_I4_2 || c == Code.Ldc_I4_3 || c == Code.Ldc_I4_4 ||
               c == Code.Ldc_I4_5 || c == Code.Ldc_I4_6 || c == Code.Ldc_I4_7 ||
               c == Code.Ldc_I4_8 || c == Code.Ldc_I4_S || c == Code.Ldc_I4;
    }

    static int Main(string[] args)
    {
        if (args.Length != 4)
        {
            Console.Error.WriteLine("usage: PatchField.exe <in.dll> <out.dll> <FIELD_NAME> <VALUE>");
            return 2;
        }

        string inPath = args[0];
        string outPath = args[1];
        string fieldName = args[2];

        int value;
        if (!int.TryParse(args[3], out value))
        {
            Console.Error.WriteLine("VALUE must be an integer");
            return 2;
        }
        if (value < -128 || value > 127)
        {
            Console.Error.WriteLine("VALUE must fit in sbyte (-128..127) for ldc.i4.s");
            return 2;
        }

        if (!File.Exists(inPath))
        {
            Console.Error.WriteLine("input not found: " + inPath);
            return 2;
        }

        AssemblyDefinition asm =
            AssemblyDefinition.ReadAssembly(inPath, new ReaderParameters());

        TypeDefinition type = asm.MainModule.Types
            .FirstOrDefault(t => t.Name == "AvatarAnimatorController");

        if (type == null)
        {
            Console.Error.WriteLine("AvatarAnimatorController not found");
            return 3;
        }

        FieldDefinition field = type.Fields.FirstOrDefault(f => f.Name == fieldName);
        if (field == null)
        {
            Console.Error.WriteLine("field not found: " + fieldName);
            return 3;
        }
        Console.WriteLine("target field token: 0x" +
            field.MetadataToken.ToString());

        MethodDefinition ctor = type.Methods
            .FirstOrDefault(m => m.IsConstructor && m.IsRuntimeSpecialName);

        if (ctor == null || !ctor.HasBody)
        {
            Console.Error.WriteLine(".ctor not found / no body");
            return 3;
        }

        var instructions = ctor.Body.Instructions;
        int patched = 0;

        for (int i = 0; i + 1 < instructions.Count; i++)
        {
            Instruction cur = instructions[i];
            Instruction next = instructions[i + 1];

            if (next.OpCode.Code != Code.Stfld) continue;

            object operand = next.Operand;
            FieldReference fr = operand as FieldReference;
            if (fr == null) continue;
            if (fr.Name != fieldName) continue;

            if (!IsLdcI4(cur.OpCode.Code)) continue;

            string before = cur.OpCode.Name + " " + Convert.ToString(cur.Operand);

            cur.OpCode = OpCodes.Ldc_I4_S;
            cur.Operand = (sbyte)value;

            Console.WriteLine("  " + before + "  ->  ldc.i4.s " + value +
                              "  ; stfld " + fr.Name);
            patched++;
        }

        if (patched == 0)
        {
            Console.Error.WriteLine("no instruction matched field: " + fieldName);
            return 4;
        }

        asm.Write(outPath, new WriterParameters());

        Console.WriteLine("patched " + patched + " site(s)");
        Console.WriteLine("written: " + outPath);
        return 0;
    }
}
