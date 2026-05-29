package ai.louis.shell.core;

import java.util.List;

public record ParsedInput(
        BrainInput brainInput,
        String taskType,
        List<String> subTasks,
        List<String> mathExpressions,
        String questionFocus,
        List<String> sentences) {

    public ParsedInput {
        subTasks = subTasks == null ? List.of() : List.copyOf(subTasks);
        mathExpressions = mathExpressions == null ? List.of() : List.copyOf(mathExpressions);
        sentences = sentences == null ? List.of() : List.copyOf(sentences);
        questionFocus = questionFocus == null ? "" : questionFocus;
    }
}
