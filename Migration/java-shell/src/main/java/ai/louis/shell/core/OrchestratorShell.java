package ai.louis.shell.core;

import java.util.List;
import java.util.OptionalDouble;

public final class OrchestratorShell {
    private final EngineGateway engineGateway;

    public OrchestratorShell(EngineGateway engineGateway) {
        this.engineGateway = engineGateway;
    }

    public List<String> boot() {
        return List.of(
                "[+] Java shell bootstrap",
                "[+] Routing contract",
                "[+] Analytical parser contract",
                "[+] Native engine facade pending bridge");
    }

    public ParsedInput parse(BrainInput input) {
        return engineGateway.parse(input);
    }

    public RouteDecision route(BrainInput input, OptionalDouble querySpecificityScore) {
        return engineGateway.route(input, querySpecificityScore);
    }

    public ClassifiedInput classify(String text) {
        return engineGateway.classify(text);
    }

    public MemoryToken storeMemory(MemoryStoreRequest request) {
        return engineGateway.storeMemory(request);
    }

    public SearchResult searchMemory(String query, int topK, String topic) {
        return engineGateway.searchMemory(query, topK, topic);
    }
}
