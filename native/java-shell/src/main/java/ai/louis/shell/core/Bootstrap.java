package ai.louis.shell.core;

import java.util.List;
import java.util.OptionalDouble;

public final class Bootstrap {
    private Bootstrap() {
    }

    public static void main(String[] args) {
        IntentRouter router = new IntentRouter(RoutingConfig.defaults());
        AnalyticalParser parser = new AnalyticalParser();
        PrototypeEngineGateway engine = new PrototypeEngineGateway(router, parser);
        OrchestratorShell shell = new OrchestratorShell(engine);
        ClassifiedInput classified = shell.classify("open chrome");
        BrainInput input = new BrainInput("open chrome", classified.intent(), classified.confidence(), classified.entities(), classified.tokens(), classified.keywords(), null, null);
        RouteDecision decision = shell.route(input, OptionalDouble.of(0.72));
        ParsedInput parsed = shell.parse(input);
        MemoryToken token = shell.storeMemory(new MemoryStoreRequest("Q: open chrome\nA: Opening chrome.", "bootstrap", 0.8, SpecificityTier.SS, ConfirmationTier.INFERRED, "apps", List.of("command"), List.of()));
        SearchResult search = shell.searchMemory("chrome", 3, "");
        System.out.printf("mode=%s analytical=%s creative=%s tier=%s task=%s intent=%s memory=%d stored=%s%n",
                decision.mode(),
                decision.activateAnalytical(),
                decision.activateCreative(),
            decision.specificityTier(),
            parsed.taskType(),
            classified.intent(),
            search.total(),
            token.id());
    }
}


