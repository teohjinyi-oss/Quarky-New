package ai.louis.shell.core;

public record MemoryResult(boolean success, String tier, String action, Object data, String message) {
}
