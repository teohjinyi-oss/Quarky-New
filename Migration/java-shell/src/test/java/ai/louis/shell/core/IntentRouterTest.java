package ai.louis.shell.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.OptionalDouble;
import org.junit.jupiter.api.Test;

class IntentRouterTest {
    private final IntentRouter router = new IntentRouter(RoutingConfig.defaults());

    @Test
    void routesSpecificitySsToFastAnalytical() {
        BrainInput input = new BrainInput("what is python", "question", 0.61);

        RouteDecision decision = router.route(input, OptionalDouble.of(0.70));

        assertEquals("fast", decision.mode());
        assertEquals("SS", decision.specificityTier());
        assertTrue(decision.activateAnalytical());
        assertFalse(decision.activateCreative());
    }

    @Test
    void routesCreativeIntentWithoutSpecificityToCreativeMode() {
        BrainInput input = new BrainInput("write me a poem", "creative", 0.90);

        RouteDecision decision = router.route(input, OptionalDouble.empty());

        assertEquals("creative", decision.mode());
        assertFalse(decision.activateAnalytical());
        assertTrue(decision.activateCreative());
    }

    @Test
    void routesLowConfidenceTaskToDeepMode() {
        BrainInput input = new BrainInput("help me plan my week", "task", 0.30);

        RouteDecision decision = router.route(input, OptionalDouble.empty());

        assertEquals("deep", decision.mode());
        assertTrue(decision.activateAnalytical());
        assertTrue(decision.activateCreative());
    }
}
