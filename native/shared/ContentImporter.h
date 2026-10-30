// GPL-2.0: platform-independent installation of original OpenTTD resource files.
#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace ottd::content {
enum Kind : uint32_t {
 Save = 1, Scenario = 2, Heightmap = 4, NewGRF = 8, Baseset = 16,
 AI = 32, AILibrary = 64, GameScript = 128, GameLibrary = 256,
};
struct Limits {
 uint64_t input_bytes = 256ULL * 1024 * 1024;
 uint64_t expanded_bytes = 1024ULL * 1024 * 1024;
 uint64_t entries = 10000;
 uint64_t expansion_ratio = 100;
};
struct Result {
 std::string name;
 uint32_t kinds = 0;
 uint64_t bytes = 0;
 std::vector<std::string> installed_paths;
 bool includes_scripts = false;
};
class Error : public std::runtime_error {
public:
 explicit Error(const std::string &message) : std::runtime_error(message) {}
};
struct Options {
 Limits limits;
 std::function<bool()> cancelled;
 // NFC normalization plus case folding, supplied by each platform's Unicode
 // implementation. Without one, archive entry names must be ASCII.
 std::function<std::string(const std::string &)> path_key;
};

// Copies, validates and stages before publication. No gameplay or script code
// executes here. The original engine scanners validate installed game content.
Result Import(const std::filesystem::path &source,
              const std::filesystem::path &game_root, const Options &options = {});
// Run before starting original scanners. Incomplete transactions are moved into
// quarantine, never silently activated or used to replace player originals.
void Recover(const std::filesystem::path &game_root);
}
