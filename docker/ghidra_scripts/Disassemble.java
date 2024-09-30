import java.io.File;
import java.io.IOException;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.exporter.AsciiExporter;

public class Disassemble extends GhidraScript {
    private static Logger log;

    public Disassemble() {
        log = LogManager.getLogger(Disassemble.class);
    }

    public void export(String filename) {
        File outputFile = new File(filename);
        AsciiExporter asciiExporter = new AsciiExporter();
        asciiExporter.setExporterServiceProvider(state.getTool());

        try {
            asciiExporter.export(outputFile, currentProgram, null, monitor);
        } catch (IOException e) {
            log.error("Failed writing disassembled code as output", e);
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        export(args[0]);
    }
}