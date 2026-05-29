package ai.louis.shell.core;

import java.util.List;
import java.util.Map;

public record BrainResult(
        String source,
        String response,
        double confidence,
        List<String> reasoning,
        Map<String, Object> metadata,
        double durationMs) {

    public BrainResult {
        reasoning = reasoning == null ? List.of() : List.copyOf(reasoning);
        metadata = metadata == null ? Map.of() : Map.copyOf(metadata);
    }
}
