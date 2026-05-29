package ai.louis.shell.core;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.regex.Pattern;

public final class PrototypeEngineGateway implements EngineGateway {
    private static final Pattern COMMAND_RE = Pattern.compile("\\b(open|close|launch|run|set|mute|restart|shutdown|search)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern QUESTION_RE = Pattern.compile("^(what|how|why|when|where|who|can|is|are)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern CREATIVE_RE = Pattern.compile("\\b(poem|joke|story|brainstorm|imagine|invent|creative)\\b", Pattern.CASE_INSENSITIVE);

    private final IntentRouter router;
    private final AnalyticalParser parser;
    private final List<MemoryToken> memory = new ArrayList<>();

    public PrototypeEngineGateway(IntentRouter router, AnalyticalParser parser) {
        this.router = router;
        this.parser = parser;
    }

    @Override
    public RouteDecision route(BrainInput input, OptionalDouble querySpecificityScore) {
        return router.route(input, querySpecificityScore);
    }

    @Override
    public ParsedInput parse(BrainInput input) {
        return parser.parse(input);
    }

    @Override
    public ClassifiedInput classify(String text) {
        String normalized = text == null ? "" : text.trim();
        String lower = normalized.toLowerCase(Locale.ROOT);
        List<String> tokens = lower.isBlank() ? List.of() : List.of(lower.split("\\s+"));
        List<String> keywords = tokens.stream().filter(token -> token.length() > 2).toList();
        Map<String, List<String>> entities = Map.of();

        if (normalized.isBlank()) {
            return new ClassifiedInput(normalized, "task", 0.0, entities, tokens, keywords, "rules");
        }
        if (CREATIVE_RE.matcher(lower).find()) {
            return new ClassifiedInput(normalized, "creative", 0.88, entities, tokens, keywords, "rules");
        }
        if (COMMAND_RE.matcher(lower).find()) {
            return new ClassifiedInput(normalized, "command", 0.86, entities, tokens, keywords, "rules");
        }
        if (QUESTION_RE.matcher(lower).find()) {
            return new ClassifiedInput(normalized, "question", 0.74, entities, tokens, keywords, "rules");
        }
        return new ClassifiedInput(normalized, "task", 0.42, entities, tokens, keywords, "rules");
    }

    @Override
    public MemoryToken storeMemory(MemoryStoreRequest request) {
        MemoryToken token = new MemoryToken(
                null,
                request.text(),
                request.specificity(),
                request.confirmation(),
                request.importance(),
                1,
                null,
                0.5,
                request.source(),
                request.topic(),
                request.relatedTo(),
                request.tags(),
                null);
        memory.add(token);
        return token;
    }

    @Override
    public SearchResult searchMemory(String query, int topK, String topic) {
        String normalizedQuery = query == null ? "" : query.toLowerCase(Locale.ROOT);
        List<String> queryTerms = normalizedQuery.isBlank() ? List.of() : List.of(normalizedQuery.split("\\s+"));

        List<MemoryToken> ranked = memory.stream()
                .filter(token -> topic == null || topic.isBlank() || topic.equalsIgnoreCase(token.topic()))
                .sorted(Comparator.comparingDouble((MemoryToken token) -> score(queryTerms, token)).reversed())
                .limit(Math.max(1, topK))
                .toList();

        Map<String, Integer> sources = new HashMap<>();
        sources.put("prototype", ranked.size());
        return new SearchResult(ranked, sources);
    }

    @Override
    public List<String> healthChecks() {
        return List.of(
                "prototype-engine: ready",
                "classification-core: ready",
                "memory-core: ready",
                "parser-core: ready",
                "routing-core: ready");
    }

    private double score(List<String> queryTerms, MemoryToken token) {
        if (queryTerms.isEmpty()) {
            return 0.0;
        }
        String haystack = (token.text() + " " + token.topic()).toLowerCase(Locale.ROOT);
        long matched = queryTerms.stream().filter(haystack::contains).count();
        return matched + token.importance();
    }
}
