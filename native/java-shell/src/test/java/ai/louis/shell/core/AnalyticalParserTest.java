package ai.louis.shell.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class AnalyticalParserTest {
    private final AnalyticalParser parser = new AnalyticalParser();

    @Test
    void detectsDefinitionFocus() {
        BrainInput input = new BrainInput(
                "What is a computer?",
                "question",
                0.70,
                null,
                List.of("what", "computer"),
                List.of("computer"),
                null,
                null);

        ParsedInput parsed = parser.parse(input);

        assertEquals("definition", parsed.taskType());
        assertEquals("computer", parsed.questionFocus());
        assertEquals(1, parsed.sentences().size());
    }

    @Test
    void decomposesMultiStepInput() {
        BrainInput input = new BrainInput(
                "open chrome and then search for javafx also save the link",
                "task",
                0.50,
                null,
                null,
                List.of("open", "chrome", "search", "javafx", "save", "link"),
                null,
                null);

        ParsedInput parsed = parser.parse(input);

        assertTrue(parsed.subTasks().size() >= 2);
        assertEquals("general", parsed.taskType());
    }

    @Test
    void detectsMathExpressions() {
        BrainInput input = new BrainInput(
                "calculate 5 + 3",
                "question",
                0.40,
                null,
                null,
                List.of("calculate", "5", "3"),
                null,
                null);

        ParsedInput parsed = parser.parse(input);

        assertEquals("math", parsed.taskType());
        assertFalse(parsed.mathExpressions().isEmpty());
    }
}
