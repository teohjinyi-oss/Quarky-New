package ai.louis.shell.core;

import java.util.List;
import java.util.OptionalDouble;

public interface EngineGateway {
    RouteDecision route(BrainInput input, OptionalDouble querySpecificityScore);

    ParsedInput parse(BrainInput input);

    ClassifiedInput classify(String text);

    MemoryToken storeMemory(MemoryStoreRequest request);

    SearchResult searchMemory(String query, int topK, String topic);

    List<String> healthChecks();
}
