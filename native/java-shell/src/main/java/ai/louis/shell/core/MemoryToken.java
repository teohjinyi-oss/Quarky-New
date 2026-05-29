package ai.louis.shell.core;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record MemoryToken(
        String id,
        String text,
        SpecificityTier specificity,
        ConfirmationTier confirmation,
        double importance,
        int frequency,
        Instant recency,
        double contextRelevance,
        String source,
        String topic,
        List<String> relatedIds,
        List<String> tags,
        Instant createdAt) {

    public MemoryToken {
        id = id == null || id.isBlank() ? UUID.randomUUID().toString().substring(0, 12) : id;
        text = text == null ? "" : text;
        specificity = specificity == null ? SpecificityTier.GG : specificity;
        confirmation = confirmation == null ? ConfirmationTier.UNVERIFIED : confirmation;
        importance = Math.max(0.0, Math.min(1.0, importance));
        frequency = Math.max(1, frequency);
        recency = recency == null ? Instant.now() : recency;
        contextRelevance = Math.max(0.0, Math.min(1.0, contextRelevance));
        source = source == null ? "" : source;
        topic = topic == null ? "" : topic;
        relatedIds = relatedIds == null ? List.of() : List.copyOf(relatedIds);
        tags = tags == null ? List.of() : List.copyOf(tags);
        createdAt = createdAt == null ? Instant.now() : createdAt;
    }

    public MemoryToken(String text, String source, double importance, String topic, List<String> tags) {
        this(null, text, SpecificityTier.GG, ConfirmationTier.UNVERIFIED, importance, 1, Instant.now(), 0.5, source, topic, List.of(), tags, Instant.now());
    }
}
