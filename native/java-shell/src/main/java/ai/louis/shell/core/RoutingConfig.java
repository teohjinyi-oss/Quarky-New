package ai.louis.shell.core;

public record RoutingConfig(
        double fastModeThreshold,
        double deepModeThreshold,
        int maxInputLengthFast) {

    public static RoutingConfig defaults() {
        return new RoutingConfig(0.8, 0.5, 100);
    }
}
