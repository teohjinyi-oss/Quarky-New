package ai.louis.shell.core;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public record BrainInput(
        String text,
        String intent,
        double confidence,
        Map<String, List<String>> entities,
        List<String> tokens,
        List<String> keywords,
        Map<String, Object> context,
        Instant timestamp) {

    public BrainInput {
        entities = entities == null ? Map.of() : Map.copyOf(entities);
        tokens = tokens == null ? List.of() : List.copyOf(tokens);
        keywords = keywords == null ? List.of() : List.copyOf(keywords);
        context = context == null ? Map.of() : Map.copyOf(context);
        timestamp = timestamp == null ? Instant.now() : timestamp;
    }

    public BrainInput(String text, String intent, double confidence) {
        this(text, intent, confidence, Map.of(), List.of(), List.of(), Map.of(), Instant.now());
    }
}
