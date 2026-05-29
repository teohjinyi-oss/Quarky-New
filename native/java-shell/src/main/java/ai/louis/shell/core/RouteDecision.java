package ai.louis.shell.core;

public record RouteDecision(
        boolean activateAnalytical,
        boolean activateCreative,
        String mode,
        String reason,
        BrainInput brainInput,
        String specificityTier) {

    public static RouteDecision analyticalFast(BrainInput brainInput, String reason, String specificityTier) {
        return new RouteDecision(true, false, "fast", reason, brainInput, specificityTier);
    }

    public static RouteDecision dualDeep(BrainInput brainInput, String reason, String specificityTier) {
        return new RouteDecision(true, true, "deep", reason, brainInput, specificityTier);
    }

    public static RouteDecision creativePrimary(BrainInput brainInput, String reason, String specificityTier) {
        return new RouteDecision(true, true, "creative", reason, brainInput, specificityTier);
    }
}
