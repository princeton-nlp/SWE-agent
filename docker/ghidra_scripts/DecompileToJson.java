import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.HashMap;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;

import com.google.gson.*;

public class DecompileToJson extends GhidraScript {
    private static Logger log;

    public DecompileToJson() {
        log = LogManager.getLogger(DecompileToJson.class);
    }

    public String find_main(HashMap<String, String> function_map) {
        // Find the `main` function from the `__libc_start_main` call
        if (!function_map.containsKey("entry")) return null;
        String entry =  function_map.get("entry");
        int libc = entry.indexOf("__libc_start_main(");
        if (libc == -1) return null;
        int funcend = entry.indexOf(',', libc);
        if (funcend == -1) return null;
        return entry.substring(libc + 18, funcend);
    }

    public void export(String filename) {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        File outputFile = new File(filename);
        String main_func = null;
        HashMap<String, String> function_map = new HashMap<String, String>();
        HashMap<String, String> address_map = new HashMap<String, String>();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);

        for (var func : currentProgram.getListing().getFunctions(Boolean.TRUE)) {
            DecompileResults res = ifc.decompileFunction(func,0,monitor);
            if (!res.decompileCompleted()) {
                System.err.println(res.getErrorMessage());
                continue;
            }
            String code = res.getDecompiledFunction().getC();
            function_map.put(func.getName(), code);
            address_map.put(func.getEntryPoint().toString(), func.getName());
            System.out.println(func.getName());
        }

        if (!function_map.containsKey("main"))
            main_func = find_main(function_map);

        //HashMap<String, HashMap<String, String>> json_data = new HashMap<String, HashMap<String, String>>();
        HashMap<String, Object> json_data = new HashMap<String, Object>();
        json_data.put("functions", function_map);
        json_data.put("addresses", address_map);
        if (main_func != null)
            json_data.put("main", main_func);
        // Convert the HashMap to JSON
        String json = gson.toJson(json_data);

        // Write JSON to file
        try (FileWriter writer = new FileWriter(outputFile)) {
            writer.write(json);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        export(args[0]);
    }
}
