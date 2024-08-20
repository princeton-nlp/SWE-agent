import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.Option;
import ghidra.app.util.OptionException;
import ghidra.app.util.exporter.CppExporter;
import ghidra.app.util.exporter.ExporterException;

public class Decompile extends GhidraScript {
    private static Logger log;

    public Decompile() {
        log = LogManager.getLogger(Decompile.class);
    }

    public void export(String filename) {
        File outputFile = new File(filename);
        CppExporter cppExporter = new CppExporter();
        cppExporter.setExporterServiceProvider(state.getTool());

        List<Option> options = new ArrayList<Option>();
        Option cppExportHeaderOption =
                new Option(CppExporter.CREATE_HEADER_FILE, Boolean.FALSE);
        options.add(cppExportHeaderOption);
        try {
            cppExporter.setOptions(options);
        } catch (OptionException e) {
            log.error("Unable to set cppExporter options", e);
            return;
        }

        try {
            cppExporter.export(outputFile, currentProgram, null, monitor);
        } catch (IOException e) {
            log.error("Failed writing decompiled code as output", e);
        } catch (ExporterException e) {
            log.error("Failed to export with cppExporter", e);
        }
    }

    @Override
    public void run() throws Exception {
        // IngredientDescription[] ingredients = getIngredientDescriptions();
        // for (IngredientDescription ingredient : ingredients) {
        //     state.addParameter(ingredient.getID(), ingredient.getLabel(),
        //             ingredient.getType(), ingredient.getDefaultValue());
        // }

        String[] args = getScriptArgs();
        export(args[0]);
    }
}