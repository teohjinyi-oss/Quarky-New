package ai.louis.shell.core;

import java.util.List;
import java.util.Map;

public record ClassifiedInput(
        String raw,
        String intent,
        double confidence,
        Map<String, List<String>> entities,
        List<String> tokens,
        List<String> keywords,
        String method) {

    public ClassifiedInput {
        raw = raw == null ? "" : raw;
        intent = intent == null ? "task" : intent;
        entities = entities == null ? Map.of() : Map.copyOf(entities);
        tokens = tokens == null ? List.of() : List.copyOf(tokens);
        keywords = keywords == null ? List.of() : List.copyOf(keywords);
        method = method == null ? "rules" : method;
    }
}
