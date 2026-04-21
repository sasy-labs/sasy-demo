/* Custom C++ functors for the airline policy.

   Implements keyword/phrase classifiers used in place of @llm_check_fn
   and a passenger-count helper for the booking arity rule.

   All classifiers are case-insensitive substring matchers over a curated
   set of phrases. They are intentionally conservative — when ambiguous,
   return 0 (no match) so that benign traffic is not blocked.
*/

#include <souffle/SouffleInterface.h>
#include <cctype>
#include <cstring>
#include <string>

namespace {

// ── Utilities ───────────────────────────────────────────────────

static std::string to_lower(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) out.push_back(
        static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    return out;
}

static bool contains(const std::string& hay, const char* needle) {
    return hay.find(needle) != std::string::npos;
}

static bool any_of(const std::string& hay, const char* const* needles,
                   std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) {
        if (contains(hay, needles[i])) return true;
    }
    return false;
}

// Word-boundary check — returns true if `needle` appears in `hay`
// bracketed by a non-alphanumeric character (or start/end of string).
// Used for short tokens like "yes" to avoid matching "eyes".
static bool word_match(const std::string& hay, const char* needle) {
    std::size_t nlen = std::strlen(needle);
    std::size_t pos = 0;
    while (true) {
        pos = hay.find(needle, pos);
        if (pos == std::string::npos) return false;
        bool left_ok  = pos == 0 ||
            !std::isalnum(static_cast<unsigned char>(hay[pos - 1]));
        bool right_ok = pos + nlen == hay.size() ||
            !std::isalnum(static_cast<unsigned char>(hay[pos + nlen]));
        if (left_ok && right_ok) return true;
        pos += 1;
    }
}

// ── JSON array counter ──────────────────────────────────────────

// Count top-level elements of a JSON array found at key `field`
// in the object `json`. Returns 0 if the field is missing or not
// an array. Handles nested objects, arrays, and strings.
static int count_json_array_elements(const std::string& json,
                                     const char* field) {
    // Build "\"<field>\"" and locate it as a key.
    std::string needle;
    needle.reserve(std::strlen(field) + 2);
    needle.push_back('"');
    needle.append(field);
    needle.push_back('"');
    std::size_t kpos = json.find(needle);
    if (kpos == std::string::npos) return 0;
    // Skip past the key and the colon.
    std::size_t p = kpos + needle.size();
    while (p < json.size() && json[p] != ':') ++p;
    if (p >= json.size()) return 0;
    ++p; // skip ':'
    while (p < json.size() &&
           (json[p] == ' ' || json[p] == '\t' ||
            json[p] == '\n' || json[p] == '\r')) ++p;
    if (p >= json.size() || json[p] != '[') return 0;
    ++p; // skip '['
    int depth = 1;
    int count = 0;
    bool saw_element = false;
    while (p < json.size() && depth > 0) {
        char c = json[p];
        if (c == '"') {
            saw_element = true;
            ++p;
            while (p < json.size() && json[p] != '"') {
                if (json[p] == '\\' && p + 1 < json.size()) ++p;
                ++p;
            }
            if (p < json.size()) ++p;
            continue;
        }
        if (c == '[' || c == '{') { saw_element = true; ++depth; ++p; continue; }
        if (c == ']') {
            --depth;
            ++p;
            if (depth == 0 && saw_element) ++count;
            continue;
        }
        if (c == '}') { --depth; ++p; continue; }
        if (c == ',' && depth == 1) {
            ++count;
            saw_element = false;
            ++p;
            continue;
        }
        if (!std::isspace(static_cast<unsigned char>(c))) saw_element = true;
        ++p;
    }
    return count;
}

} // namespace

extern "C" {

// ── Bag request ────────────────────────────────────────────────

souffle::RamDomain user_requested_bags(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    static const char* kPhrases[] = {
        "checked bag", "checked bags",
        "checked luggage", "check a bag", "check bags",
        "add bag", "add bags", "add baggage", "add luggage",
        "with bag", "with bags", "with baggage", "with luggage",
        "include bag", "include bags", "include baggage",
        "want bag", "want bags", "want baggage", "want luggage",
        "need bag", "need bags", "need baggage", "need luggage",
        "have bag", "have bags", "have baggage", "have luggage",
        "bring bag", "bring bags", "bring luggage",
        "extra bag", "extra bags", "extra baggage", "extra luggage",
        "one bag", "two bags", "three bags", "four bags", "five bags",
        "1 bag", "2 bags", "3 bags", "4 bags", "5 bags",
    };
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);
    bool hit = any_of(low, kPhrases,
                      sizeof(kPhrases) / sizeof(kPhrases[0]));
    return hit ? 1u : 0u;
}

// ── Affirmative confirmation ───────────────────────────────────

souffle::RamDomain user_confirmed_yes(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);

    // Word-level confirmatives — guarded by word boundaries so
    // "eyes"/"nope" do not produce false positives.
    static const char* kWords[] = {
        "yes", "yep", "yeah", "yup", "ok", "okay",
        "sure", "confirm", "confirmed", "correct", "affirmative",
    };
    for (const char* w : kWords) {
        if (word_match(low, w)) return 1u;
    }

    // Substring phrases.
    static const char* kPhrases[] = {
        "go ahead", "please proceed", "proceed", "sounds good",
        "please do", "please book", "please cancel",
        "please update", "please change", "please modify",
        "i confirm", "do it", "let's do it", "that's correct",
        "thats correct",
    };
    return any_of(low, kPhrases,
                  sizeof(kPhrases) / sizeof(kPhrases[0])) ? 1u : 0u;
}

// ── User-error cancellation reason ─────────────────────────────

souffle::RamDomain user_error_reason(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    static const char* kPhrases[] = {
        "accidentally", "by accident",
        "mistake", "mistakenly", "my bad",
        "wrong flight", "wrong date", "wrong destination",
        "wrong city", "wrong airport",
        "double book", "double-book", "double booked", "double-booked",
        "booked twice", "booked two",
        "meant to book", "meant to pick", "meant to choose",
        "picked the wrong", "chose the wrong", "selected the wrong",
        "clicked the wrong", "hit the wrong",
        "didn't mean to", "did not mean to",
    };
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);
    return any_of(low, kPhrases,
                  sizeof(kPhrases) / sizeof(kPhrases[0])) ? 1u : 0u;
}

// ── Trivial social cancellation reason ─────────────────────────

souffle::RamDomain trivial_social_reason(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    static const char* kPhrases[] = {
        "birthday party", "birthday",
        "party", "parties", "celebration",
        "concert", "festival", "show", "gig",
        "reunion", "get-together", "get together",
        "sporting event", "baseball game", "football game",
        "basketball game", "soccer game", "hockey game",
        "went on vacation",
    };
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);
    return any_of(low, kPhrases,
                  sizeof(kPhrases) / sizeof(kPhrases[0])) ? 1u : 0u;
}

// ── Insurance-covered cancellation reason ──────────────────────

souffle::RamDomain covered_cancellation_reason(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    static const char* kPhrases[] = {
        // Health-related
        "sick", "illness", "ill", "ill.",
        "hospital", "hospitalized", "hospitalised",
        "surgery", "injury", "injured", "emergency room",
        "medical", "health", "doctor", "flu", "covid",
        "pregnant", "pregnancy",
        // Weather-related
        "weather", "storm", "hurricane", "blizzard", "snowstorm",
        "typhoon", "flood", "flooding", "earthquake",
        // Significant personal circumstances
        "funeral", "death in the family", "family emergency",
        "work emergency", "business emergency",
        "schedule conflict", "scheduling conflict",
        "change of plans", "change of plan",
        "plans changed",
    };
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);
    return any_of(low, kPhrases,
                  sizeof(kPhrases) / sizeof(kPhrases[0])) ? 1u : 0u;
}

// ── User-requested compensation ────────────────────────────────

souffle::RamDomain user_requested_compensation(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain text_sym)
{
    static const char* kPhrases[] = {
        "compensation", "compensate",
        "certificate", "travel certificate",
        "voucher", "credit for the trouble", "credit for the delay",
        "reimburse", "reimbursement",
        "refund for the delay", "refund for the trouble",
        "make it up to me", "make it right",
        "goodwill gesture",
    };
    const std::string& raw = symbolTable->decode(text_sym);
    std::string low = to_lower(raw);
    return any_of(low, kPhrases,
                  sizeof(kPhrases) / sizeof(kPhrases[0])) ? 1u : 0u;
}

// ── Passenger counter ──────────────────────────────────────────

souffle::RamDomain count_passengers(
    souffle::SymbolTable* symbolTable,
    souffle::RecordTable* /*recordTable*/,
    souffle::RamDomain args_sym)
{
    const std::string& args = symbolTable->decode(args_sym);
    int n = count_json_array_elements(args, "passengers");
    return static_cast<souffle::RamDomain>(n);
}

} // extern "C"

// ── First flight number extraction ────────────────────────────

// Forward-declare common functor (C linkage, defined in functors_common.cpp)
extern "C" souffle::RamDomain json_get_str(
    souffle::SymbolTable*, souffle::RecordTable*,
    souffle::RamDomain, souffle::RamDomain);

extern "C" souffle::RamDomain extract_first_flight(
    souffle::SymbolTable* st, souffle::RecordTable* rt, souffle::RamDomain json_sym)
{
    return json_get_str(st, rt, json_sym, st->encode("flight_number"));
}
