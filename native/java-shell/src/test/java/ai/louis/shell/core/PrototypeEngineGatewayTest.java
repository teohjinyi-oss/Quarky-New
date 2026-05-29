package ai.louis.shell.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class PrototypeEngineGatewayTest {
    private final PrototypeEngineGateway gateway = new PrototypeEngineGateway(
            new IntentRouter(RoutingConfig.defaults()),
            new AnalyticalParser());

    @Test
    void classifiesCommandText() {
        ClassifiedInput result = gateway.classify("open file explorer");
        assertEquals("command", result.intent());
        assertTrue(result.confidence() > 0.7);
    }

    @Test
    void storesAndFindsMemory() {
        MemoryToken stored = gateway.storeMemory(new MemoryStoreRequest(
                "Q: what is javafx\nA: JavaFX is a Java UI toolkit.",
                "test",
                0.9,
                SpecificityTier.GS,
                ConfirmationTier.INFERRED,
                "ui",
                List.of("javafx"),
                List.of()));

        SearchResult result = gateway.searchMemory("javafx", 5, "ui");

        assertNotNull(stored.id());
        assertFalse(result.tokens().isEmpty());
        assertEquals(stored.id(), result.best().id());
    }
}
