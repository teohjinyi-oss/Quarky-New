package ai.louis.shell.core;

public record SpinalResult(
        BrainResult analytical,
        BrainResult creative,
        String routeDecision,
        String inputIntent,
        String inputText) {
}
