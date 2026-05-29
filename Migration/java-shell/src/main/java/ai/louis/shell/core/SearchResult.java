package ai.louis.shell.core;

import java.util.List;
import java.util.Map;

public record SearchResult(List<MemoryToken> tokens, Map<String, Integer> sources) {
    public SearchResult {
        tokens = tokens == null ? List.of() : List.copyOf(tokens);
        sources = sources == null ? Map.of() : Map.copyOf(sources);
    }

    public int total() {
        return tokens.size();
    }

    public MemoryToken best() {
        return tokens.isEmpty() ? null : tokens.getFirst();
    }
}
