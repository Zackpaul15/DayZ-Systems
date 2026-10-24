// Batch queries against an already analysed Ghidra program (read-only).
// Usage (headless): -postScript BatchDecompile.java TASK_FILE OUT_FILE
// Task file, one per line ('#' starts a comment):
//   decompile <FUN_xxxxxxxx | 0xADDR | symbol name>
//   xrefs     <0xADDR>              references to an address
//   bytes     <0xADDR> <length>     hex dump of memory
//   string    <0xADDR>              NUL-terminated ASCII string at an address
// Output: text sections headed by '=== <task line> ===' in OUT_FILE.
import java.io.File;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;

public class BatchDecompile extends GhidraScript {

	private Address addr(String tok) throws Exception {
		if (tok.startsWith("FUN_")) {
			return toAddr(tok.substring(4));
		}
		if (tok.startsWith("0x")) {
			return toAddr(tok.substring(2));
		}
		List<Symbol> syms = currentProgram.getSymbolTable().getGlobalSymbols(tok);
		if (!syms.isEmpty()) {
			return syms.get(0).getAddress();
		}
		return toAddr(tok);
	}

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		List<String> lines = Files.readAllLines(new File(args[0]).toPath());
		DecompInterface di = new DecompInterface();
		di.openProgram(currentProgram);
		try (PrintWriter out = new PrintWriter(new File(args[1]), "UTF-8")) {
			for (String raw : lines) {
				String line = raw.trim();
				if (line.isEmpty() || line.startsWith("#")) {
					continue;
				}
				String[] p = line.split("\\s+");
				out.println("=== " + line + " ===");
				try {
					if (p[0].equals("symbols")) {
						// symbols <substring>: global symbols whose name contains the text
						int n = 0;
						for (Symbol s : currentProgram.getSymbolTable().getAllSymbols(true)) {
							if (s.getName(true).contains(p[1])) {
								out.println(s.getAddress() + " " + s.getName(true));
								if (++n > 5000) {
									break;
								}
							}
						}
						out.println();
						continue;
					}
					if (p[0].equals("funcs")) {
						// funcs <0xSTART> <0xEND>: functions in the range with their sizes in bytes
						Address lo = addr(p[1]);
						Address hi = addr(p[2]);
						for (Function f : currentProgram.getFunctionManager().getFunctions(lo, true)) {
							if (f.getEntryPoint().compareTo(hi) > 0) {
								break;
							}
							out.println(f.getEntryPoint() + " " + f.getName() + " " + f.getBody().getNumAddresses());
						}
						out.println();
						continue;
					}
					if (p[0].equals("instrscan")) {
						// instrscan <text> <0xSTART> <0xEND>: instructions in the range whose text contains <text>
						Address lo = addr(p[2]);
						Address hi = addr(p[3]);
						int n = 0; // matches printed (capped), not instructions scanned
						for (ghidra.program.model.listing.Instruction ins : currentProgram.getListing()
								.getInstructions(lo, true)) {
							if (ins.getAddress().compareTo(hi) > 0 || n > 20000) {
								break;
							}
							String t = ins.toString();
							if (t.contains(p[1])) {
								n++;
								Function f = getFunctionContaining(ins.getAddress());
								out.println(ins.getAddress() + " " + t + "  [" + (f == null ? "-" : f.getName()) + "]");
							}
						}
						out.println();
						continue;
					}
					Address a = addr(p[1]);
					switch (p[0]) {
					case "vtable": {
						// vtable <0xADDR> <count>: pointers in a vtable and the functions they target
						int n = Integer.decode(p[2]);
						for (int i = 0; i < n; i++) {
							Address pa = a.add(8L * i);
							long v = getLong(pa);
							Address fa = toAddr(v);
							Function f = fa == null ? null : getFunctionAt(fa);
							out.println("[" + i + "] " + pa + " -> " + fa + " " + (f == null ? "-" : f.getName()));
						}
						break;
					}
					case "decompile": {
						Function f = getFunctionContaining(a);
						if (f == null) {
							out.println("no function at " + a);
							break;
						}
						out.println("// function " + f.getName() + " entry " + f.getEntryPoint()
								+ (f.getEntryPoint().equals(a) ? "" : " (containing " + a + ")"));
						DecompileResults r = di.decompileFunction(f, 180, monitor);
						out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC()
								: "decompile failed: " + r.getErrorMessage());
						break;
					}
					case "xrefs": {
						for (Reference ref : getReferencesTo(a)) {
							Function f = getFunctionContaining(ref.getFromAddress());
							out.println(ref.getFromAddress() + " " + ref.getReferenceType() + " "
									+ (f == null ? "-" : f.getName()));
						}
						break;
					}
					case "bytes": {
						int n = Integer.decode(p[2]);
						byte[] b = getBytes(a, n);
						StringBuilder sb = new StringBuilder();
						for (byte x : b) {
							sb.append(String.format("%02x", x));
						}
						out.println(a + ": " + sb);
						break;
					}
					case "string": {
						StringBuilder sb = new StringBuilder();
						for (int i = 0; i < 512; i++) {
							byte c = getByte(a.add(i));
							if (c == 0) {
								break;
							}
							sb.append((char) (c & 0xff));
						}
						out.println(a + ": " + sb);
						break;
					}
					default:
						out.println("unknown task " + p[0]);
					}
				} catch (Exception e) {
					out.println("error: " + e);
				}
				out.println();
			}
		}
		di.dispose();
	}
}
