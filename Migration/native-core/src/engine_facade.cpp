#include "louisai/engine/engine_facade.hpp"

#include <algorithm>
#include <format>
#include <regex>
#include <sstream>
#include <cctype>

namespace louisai::engine {

namespace {

constexpr double kFastModeThreshold = 0.8;
constexpr double kDeepModeThreshold = 0.5;
constexpr std::size_t kMaxInputLengthFast = 100;

const std::regex kMathRe(
    R"(\b\d+\s*[+\-*/%^]\s*\d+|\b(calculate|compute|solve|evaluate)\b|\bsqrt|log|sin|cos|tan\b|\b\d+\s*(plus|minus|times|divided by|to the power)\s*\d+)",
    std::regex::icase);

const std::regex kDefinitionRe(
    R"(\b(what is|what are|define|meaning of|definition of|explain what)\b)",
    std::regex::icase);

const std::regex kComparisonRe(
    R"(\b(difference between|compare|versus|vs\.?|better|worse|which one)\b)",
    std::regex::icase);

const std::regex kMultiStepSplitRe(
    R"(\b(?:and then|after that|then|also)\b)",
    std::regex::icase);

const std::regex kWhatIsFocusRe(
    R"(what (?:is|are) (?:a |an |the )?(.+?)(?:\?|$))",
    std::regex::icase);

const std::regex kCommandRe(
    R"(\b(open|close|launch|run|set|mute|restart|shutdown|search)\b)",
    std::regex::icase);

const std::regex kQuestionRe(
    R"(^(what|how|why|when|where|who|can|is|are)\b)",
    std::regex::icase);

const std::regex kCreativeRe(
    R"(\b(poem|joke|story|brainstorm|imagine|invent|creative)\b)",
    std::regex::icase);

std::string normalize(std::string text) {
    std::ranges::transform(text, text.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return text;
}

std::vector<std::string> split_words(const std::string& text) {
    std::istringstream stream(text);
    std::vector<std::string> words;
    for (std::string word; stream >> word;) {
        words.push_back(word);
    }
    return words;
}

std::string make_token_id(std::size_t index) {
    return std::format("tok{:08}", index);
}

double token_score(const std::vector<std::string>& query_terms, const Token& token) {
    const auto haystack = normalize(token.text + " " + token.topic);
    double matched = 0.0;
    for (const auto& term : query_terms) {
        if (!term.empty() && haystack.find(term) != std::string::npos) {
            matched += 1.0;
        }
    }
    return matched + token.importance;
}

std::vector<std::string> split_sentences(const std::string& text) {
    std::vector<std::string> sentences;
    std::string current;
    for (char ch : text) {
        current.push_back(ch);
        if (ch == '.' || ch == '!' || ch == '?') {
            if (!current.empty()) {
                sentences.push_back(current);
                current.clear();
            }
        }
    }
    if (!current.empty()) {
        sentences.push_back(current);
    }
    if (sentences.empty() && !text.empty()) {
        sentences.push_back(text);
    }
    return sentences;
}

std::vector<std::string> decompose(const std::string& text) {
    if (!std::regex_search(text, kMultiStepSplitRe)) {
        return {text};
    }

    std::vector<std::string> parts;
    std::sregex_token_iterator iter(text.begin(), text.end(), kMultiStepSplitRe, -1);
    std::sregex_token_iterator end;
    for (; iter != end; ++iter) {
        if (!iter->str().empty()) {
            parts.push_back(iter->str());
        }
    }
    return parts;
}

std::vector<std::string> extract_math_expressions(const std::string& text) {
    std::vector<std::string> expressions;
    for (std::sregex_iterator iter(text.begin(), text.end(), kMathRe), end; iter != end; ++iter) {
        expressions.push_back(iter->str());
    }
    return expressions;
}

std::string extract_focus(const BrainInput& input) {
    if (input.keywords.empty()) {
        return {};
    }

    std::smatch match;
    if (std::regex_search(input.text, match, kWhatIsFocusRe) && match.size() > 1) {
        return match[1].str();
    }

    std::ostringstream builder;
    for (std::size_t i = 0; i < input.keywords.size() && i < 3; ++i) {
        if (i > 0) {
            builder << ' ';
        }
        builder << input.keywords[i];
    }
    return builder.str();
}

std::string detect_task_type(const BrainInput& input) {
    if (std::regex_search(input.text, kMathRe)) {
        return "math";
    }
    if (std::regex_search(input.text, kDefinitionRe)) {
        return "definition";
    }
    if (std::regex_search(input.text, kComparisonRe)) {
        return "comparison";
    }
    if (input.intent == "command") {
        return "command";
    }
    if (input.intent == "question") {
        return "factual";
    }
    return "general";
}

}  // namespace

RouteDecision EngineFacade::route(const BrainInput& input,
                                  std::optional<double> query_specificity_score) const {
    if (query_specificity_score.has_value()) {
        const auto score = query_specificity_score.value();
        if (score >= 0.65) {
            return {.activate_analytical = true,
                    .activate_creative = false,
                    .mode = "fast",
                    .reason = std::format("Specificity SS - direct analytical answer (q={:.2f})", score),
                    .specificity_tier = "SS"};
        }
        if (score >= 0.55) {
            return {.activate_analytical = true,
                    .activate_creative = false,
                    .mode = "fast",
                    .reason = std::format("Specificity GS - analytical explain-then-answer (q={:.2f})", score),
                    .specificity_tier = "GS"};
        }
        if (score >= 0.40) {
            return {.activate_analytical = true,
                    .activate_creative = true,
                    .mode = "deep",
                    .reason = std::format("Specificity SG - both brains for broader context (q={:.2f})", score),
                    .specificity_tier = "SG"};
        }

        return {.activate_analytical = true,
                .activate_creative = true,
                .mode = "creative",
                .reason = std::format("Specificity GG - creative primary (q={:.2f})", score),
                .specificity_tier = "GG"};
    }

    if (input.intent == "creative") {
        return {.activate_analytical = false,
                .activate_creative = true,
                .mode = "creative",
                .reason = std::format("Creative intent detected (conf={:.2f})", input.confidence)};
    }

    if (input.intent == "command" && input.confidence >= kFastModeThreshold) {
        return {.activate_analytical = true,
                .activate_creative = false,
                .mode = "fast",
                .reason = std::format("Command + high confidence ({:.2f} >= {:.2f})", input.confidence, kFastModeThreshold)};
    }

    if (input.intent == "command" && input.text.size() <= kMaxInputLengthFast) {
        return {.activate_analytical = true,
                .activate_creative = false,
                .mode = "fast",
                .reason = std::format("Short command ({} chars), fast path", input.text.size())};
    }

    if (input.intent == "question" && input.confidence >= kDeepModeThreshold) {
        return {.activate_analytical = true,
                .activate_creative = false,
                .mode = "fast",
                .reason = std::format("Question + sufficient confidence ({:.2f} >= {:.2f})", input.confidence, kDeepModeThreshold)};
    }

    return {.activate_analytical = true,
            .activate_creative = true,
            .mode = "deep",
            .reason = std::format("Deep mode: intent={}, conf={:.2f} - activating both hemispheres", input.intent, input.confidence)};
}

ParsedInput EngineFacade::parse(const BrainInput& input) const {
    return ParsedInput{
        .brain_input = input,
        .task_type = detect_task_type(input),
        .sub_tasks = decompose(input.text),
        .math_expressions = extract_math_expressions(input.text),
        .question_focus = extract_focus(input),
        .sentences = split_sentences(input.text),
    };
}

ClassifiedInput EngineFacade::classify(const std::string& text) const {
    const auto normalized = normalize(text);
    const auto words = split_words(normalized);

    if (normalized.empty()) {
        return ClassifiedInput{.raw = text, .intent = "task", .confidence = 0.0, .tokens = words, .keywords = {}, .method = "rules"};
    }
    if (std::regex_search(normalized, kCreativeRe)) {
        return ClassifiedInput{.raw = text, .intent = "creative", .confidence = 0.88, .tokens = words, .keywords = words, .method = "rules"};
    }
    if (std::regex_search(normalized, kCommandRe)) {
        return ClassifiedInput{.raw = text, .intent = "command", .confidence = 0.86, .tokens = words, .keywords = words, .method = "rules"};
    }
    if (std::regex_search(normalized, kQuestionRe)) {
        return ClassifiedInput{.raw = text, .intent = "question", .confidence = 0.74, .tokens = words, .keywords = words, .method = "rules"};
    }
    return ClassifiedInput{.raw = text, .intent = "task", .confidence = 0.42, .tokens = words, .keywords = words, .method = "rules"};
}

Token EngineFacade::store_memory(const MemoryStoreRequest& request) {
    Token token{
        .id = make_token_id(memory_.size() + 1),
        .text = request.text,
        .specificity = request.specificity,
        .confirmation = request.confirmation,
        .importance = request.importance,
        .frequency = 1,
        .context_relevance = 0.5,
        .source = request.source,
        .topic = request.topic,
        .related_ids = request.related_to,
        .tags = request.tags,
    };
    memory_.push_back(token);
    return token;
}

SearchResult EngineFacade::search_memory(const std::string& query,
                                         int top_k,
                                         const std::string& topic) const {
    SearchResult result;
    const auto query_terms = split_words(normalize(query));

    auto ranked = memory_;
    ranked.erase(std::remove_if(ranked.begin(), ranked.end(), [&](const Token& token) {
        return !topic.empty() && normalize(token.topic) != normalize(topic);
    }), ranked.end());

    std::ranges::sort(ranked, [&](const Token& left, const Token& right) {
        return token_score(query_terms, left) > token_score(query_terms, right);
    });

    if (top_k > 0 && static_cast<std::size_t>(top_k) < ranked.size()) {
        ranked.resize(static_cast<std::size_t>(top_k));
    }

    result.tokens = std::move(ranked);
    result.sources["native-prototype"] = static_cast<int>(result.tokens.size());
    return result;
}

std::vector<std::string> EngineFacade::health_checks() const {
    return {
        "native-engine: initialized",
        "routing-core: ready",
        "parser-core: ready",
        "classification-core: ready",
        "memory-core: ready",
        "speech-core: pending"
    };
}

}  // namespace louisai::engine
