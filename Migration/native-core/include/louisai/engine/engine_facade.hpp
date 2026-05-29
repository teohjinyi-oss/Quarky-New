#pragma once

#include <optional>
#include <unordered_map>
#include <string>
#include <string_view>
#include <vector>

namespace louisai::engine {

struct RouteDecision {
    bool activate_analytical = false;
    bool activate_creative = false;
    std::string mode;
    std::string reason;
    std::string specificity_tier;
};

struct BrainInput {
    std::string text;
    std::string intent;
    double confidence = 0.0;
    std::vector<std::string> tokens;
    std::vector<std::string> keywords;
};

struct ParsedInput {
    BrainInput brain_input;
    std::string task_type;
    std::vector<std::string> sub_tasks;
    std::vector<std::string> math_expressions;
    std::string question_focus;
    std::vector<std::string> sentences;
};

enum class SpecificityTier {
    ss,
    gs,
    sg,
    gg,
};

enum class ConfirmationTier {
    user_confirmed,
    inferred,
    unverified,
};

struct Token {
    std::string id;
    std::string text;
    SpecificityTier specificity = SpecificityTier::gg;
    ConfirmationTier confirmation = ConfirmationTier::unverified;
    double importance = 0.5;
    int frequency = 1;
    double context_relevance = 0.5;
    std::string source;
    std::string topic;
    std::vector<std::string> related_ids;
    std::vector<std::string> tags;
};

struct SearchResult {
    std::vector<Token> tokens;
    std::unordered_map<std::string, int> sources;
};

struct MemoryStoreRequest {
    std::string text;
    std::string source = "user";
    double importance = 0.5;
    SpecificityTier specificity = SpecificityTier::gg;
    ConfirmationTier confirmation = ConfirmationTier::unverified;
    std::string topic;
    std::vector<std::string> tags;
    std::vector<std::string> related_to;
};

struct ClassifiedInput {
    std::string raw;
    std::string intent;
    double confidence = 0.0;
    std::unordered_map<std::string, std::vector<std::string>> entities;
    std::vector<std::string> tokens;
    std::vector<std::string> keywords;
    std::string method = "rules";
};

class EngineFacade {
public:
    EngineFacade() = default;

    [[nodiscard]] RouteDecision route(const BrainInput& input,
                                      std::optional<double> query_specificity_score) const;

    [[nodiscard]] ParsedInput parse(const BrainInput& input) const;

    [[nodiscard]] ClassifiedInput classify(const std::string& text) const;

    [[nodiscard]] Token store_memory(const MemoryStoreRequest& request);

    [[nodiscard]] SearchResult search_memory(const std::string& query,
                                             int top_k,
                                             const std::string& topic) const;

    [[nodiscard]] std::vector<std::string> health_checks() const;

private:
    std::vector<Token> memory_;
};

}  // namespace louisai::engine

