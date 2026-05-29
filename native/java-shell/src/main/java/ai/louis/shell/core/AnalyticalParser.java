package ai.louis.shell.core;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class AnalyticalParser {
    private static final Pattern MATH_RE = Pattern.compile(
            "\\b\\d+\\s*[+\\-*/%^]\\s*\\d+|"
                    + "\\b(calculate|compute|solve|evaluate)\\b|"
                    + "\\bsqrt|log|sin|cos|tan\\b|"
                    + "\\b\\d+\\s*(plus|minus|times|divided by|to the power)\\s*\\d+",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern DEFINITION_RE = Pattern.compile(
            "\\b(what is|what are|define|meaning of|definition of|explain what)\\b",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern COMPARISON_RE = Pattern.compile(
            "\\b(difference between|compare|versus|vs\\.?|better|worse|which one)\\b",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern MULTI_STEP_RE = Pattern.compile(
            "\\b(and then|after that|first .+ then|step by step|also)\\b",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern WHAT_IS_FOCUS_RE = Pattern.compile(
            "what (?:is|are) (?:a |an |the )?(.+?)(?:\\?|$)",
            Pattern.CASE_INSENSITIVE);

    public ParsedInput parse(BrainInput input) {
        String text = input.text() == null ? "" : input.text();
        String lower = text.toLowerCase(Locale.ROOT);

        return new ParsedInput(
                input,
                detectTaskType(lower, input.intent()),
                decompose(text),
                extractMathExpressions(text),
                extractFocus(input.keywords(), lower),
                tokenizeSentences(text));
    }

    String detectTaskType(String lower, String intent) {
        if (MATH_RE.matcher(lower).find()) {
            return "math";
        }
        if (DEFINITION_RE.matcher(lower).find()) {
            return "definition";
        }
        if (COMPARISON_RE.matcher(lower).find()) {
            return "comparison";
        }
        if ("command".equals(intent)) {
            return "command";
        }
        if ("question".equals(intent)) {
            return "factual";
        }
        return "general";
    }

    List<String> decompose(String text) {
        if (!MULTI_STEP_RE.matcher(text).find()) {
            return List.of(text);
        }

        String[] parts = text.split("(?i)\\b(?:and then|after that|then|also)\\b");
        List<String> result = new ArrayList<>();
        for (String part : parts) {
            String trimmed = part.trim();
            if (!trimmed.isEmpty()) {
                result.add(trimmed);
            }
        }
        return result;
    }

    List<String> extractMathExpressions(String text) {
        Matcher matcher = MATH_RE.matcher(text);
        List<String> expressions = new ArrayList<>();
        while (matcher.find()) {
            String match = matcher.group();
            if (match != null && !match.isBlank()) {
                expressions.add(match.trim());
            }
        }
        return expressions;
    }

    String extractFocus(List<String> keywords, String lower) {
        if (keywords == null || keywords.isEmpty()) {
            return "";
        }

        Matcher matcher = WHAT_IS_FOCUS_RE.matcher(lower);
        if (matcher.find()) {
            return matcher.group(1).trim();
        }

        return String.join(" ", keywords.stream().limit(3).toList());
    }

    List<String> tokenizeSentences(String text) {
        if (text == null || text.isBlank()) {
            return List.of();
        }
        return Arrays.stream(text.split("(?<=[.!?])\\s+|\\n+"))
                .map(String::trim)
                .filter(part -> !part.isEmpty())
                .toList();
    }
}
