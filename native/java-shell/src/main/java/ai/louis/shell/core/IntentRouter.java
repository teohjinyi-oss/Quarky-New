package ai.louis.shell.core;

import java.util.Objects;
import java.util.OptionalDouble;

public final class IntentRouter {
    private final RoutingConfig config;

    public IntentRouter(RoutingConfig config) {
        this.config = Objects.requireNonNull(config, "config");
    }

    public RouteDecision route(BrainInput brainInput, OptionalDouble querySpecificityScore) {
        Objects.requireNonNull(brainInput, "brainInput");

        if (querySpecificityScore.isPresent()) {
            RouteDecision decision = routeBySpecificity(brainInput, querySpecificityScore.getAsDouble());
            if (decision != null) {
                return decision;
            }
        }

        return routeByConfidence(brainInput);
    }

    RouteDecision routeBySpecificity(BrainInput brainInput, double querySpecificityScore) {
        if (querySpecificityScore >= 0.65) {
            return RouteDecision.analyticalFast(
                    brainInput,
                    String.format("Specificity SS - direct analytical answer (q=%.2f)", querySpecificityScore),
                    "SS");
        }

        if (querySpecificityScore >= 0.55) {
            return RouteDecision.analyticalFast(
                    brainInput,
                    String.format("Specificity GS - analytical explain-then-answer (q=%.2f)", querySpecificityScore),
                    "GS");
        }

        if (querySpecificityScore >= 0.40) {
            return RouteDecision.dualDeep(
                    brainInput,
                    String.format("Specificity SG - both brains for broader context (q=%.2f)", querySpecificityScore),
                    "SG");
        }

        return RouteDecision.creativePrimary(
                brainInput,
                String.format("Specificity GG - creative primary (q=%.2f)", querySpecificityScore),
                "GG");
    }

    RouteDecision routeByConfidence(BrainInput brainInput) {
        String intent = brainInput.intent() == null ? "" : brainInput.intent();
        double confidence = brainInput.confidence();
        int textLength = brainInput.text() == null ? 0 : brainInput.text().length();

        if ("creative".equals(intent)) {
            return new RouteDecision(
                    false,
                    true,
                    "creative",
                    String.format("Creative intent detected (conf=%.2f)", confidence),
                    brainInput,
                    "");
        }

        if ("command".equals(intent) && confidence >= config.fastModeThreshold()) {
            return RouteDecision.analyticalFast(
                    brainInput,
                    String.format("Command + high confidence (%.2f >= %.2f)", confidence, config.fastModeThreshold()),
                    "");
        }

        if ("command".equals(intent) && textLength <= config.maxInputLengthFast()) {
            return RouteDecision.analyticalFast(
                    brainInput,
                    String.format("Short command (%d chars), fast path", textLength),
                    "");
        }

        if ("question".equals(intent) && confidence >= config.deepModeThreshold()) {
            return RouteDecision.analyticalFast(
                    brainInput,
                    String.format("Question + sufficient confidence (%.2f >= %.2f)", confidence, config.deepModeThreshold()),
                    "");
        }

        return RouteDecision.dualDeep(
                brainInput,
                String.format("Deep mode: intent=%s, conf=%.2f - activating both hemispheres", intent, confidence),
                "");
    }
}
