#include "ContentImporter.h"
#include "ContentPathKey.h"
#include <nlohmann/json.hpp>
#include <iostream>
int main(int argc, char **argv)
{
 if (argc < 3) return 1;
 try {
  if (std::string(argv[1]) == "--recover") {
   ottd::content::Recover(argv[2]);
   std::cout << "{\"recovered\":true}\n";
  } else {
   ottd::content::Options options;
   options.path_key = NativeContentPathKey;
   if (argc > 3) {
    auto value = nlohmann::json::parse(argv[3]);
    options.limits.input_bytes = value.value("input", options.limits.input_bytes);
    options.limits.expanded_bytes = value.value("expanded", options.limits.expanded_bytes);
    options.limits.entries = value.value("entries", options.limits.entries);
    options.limits.expansion_ratio = value.value("ratio", options.limits.expansion_ratio);
    bool cancelled = value.value("cancelled", false);
    options.cancelled = [cancelled] { return cancelled; };
   }
   auto result = ottd::content::Import(argv[1], argv[2], options);
   std::cout << nlohmann::json{{"name", result.name}, {"kinds", result.kinds}, {"bytes", result.bytes},
    {"paths", result.installed_paths}, {"scripts", result.includes_scripts}}.dump() << '\n';
  }
  return 0;
 } catch (const std::exception &error) {
  std::cout << nlohmann::json{{"error", error.what()}}.dump() << '\n';
  return 2;
 }
}
