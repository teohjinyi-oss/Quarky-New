package ai.louis.shell.core;

import java.util.List;

public record MemoryStoreRequest(
        String text,
        String source,
        double importance,
        SpecificityTier specificity,
        ConfirmationTier confirmation,
        String topic,
        List<String> tags,
        List<String> relatedTo) {

    public MemoryStoreRequest {
        source = source == null ? "user" : source;
        specificity = specificity == null ? SpecificityTier.GG : specificity;
        confirmation = confirmation == null ? ConfirmationTier.UNVERIFIED : confirmation;
        topic = topic == null ? "" : topic;
        tags = tags == null ? List.of() : List.copyOf(tags);
        relatedTo = relatedTo == null ? List.of() : List.copyOf(relatedTo);
    }

    public MemoryStoreRequest(String text) {
        this(text, "user", 0.5, SpecificityTier.GG, ConfirmationTier.UNVERIFIED, "", List.of(), List.of());
    }
}
