// GPL-2.0. Original resource formats are installed; no gameplay is implemented here.
#include "ContentImporter.h"
#include <archive.h>
#include <archive_entry.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cctype>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <map>
#include <locale.h>
#include <memory>
#include <set>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef __APPLE__
#include <xlocale.h>
#endif
#ifdef __linux__
#include <sys/syscall.h>
#include <linux/fs.h>
#endif

namespace ottd::content {
namespace {
namespace fs = std::filesystem;
using Json = nlohmann::json;
constexpr size_t CHUNK = 65536;
struct ScopedUTF8Locale {
 locale_t locale = nullptr, previous = nullptr;
 ScopedUTF8Locale() {
  locale = newlocale(LC_CTYPE_MASK, "en_US.UTF-8", nullptr);
  if (!locale) locale = newlocale(LC_CTYPE_MASK, "C.UTF-8", nullptr);
  if (!locale) throw Error("A UTF-8 locale is required to read package filenames.");
  previous = uselocale(locale);
  if (!previous) { freelocale(locale); throw Error("Could not activate the import thread's UTF-8 locale."); }
 }
 ~ScopedUTF8Locale() { uselocale(previous); freelocale(locale); }
};
struct FD {
 int value;
 explicit FD(int value) : value(value) { if (value < 0) throw Error("Could not open an import file."); }
 ~FD() { close(value); }
 FD(const FD &) = delete;
};
std::string Lower(std::string value)
{
 for (char &c : value) if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
 return value;
}
void CheckCancelled(const Options &options)
{
 if (options.cancelled && options.cancelled()) throw Error("Import cancelled. Existing content was preserved.");
}
void CheckUTF8(const std::string &name)
{
 try { (void)Json(name).dump(); }
 catch (...) { throw Error("The package contains an invalid UTF-8 filename."); }
}
fs::path SafePath(std::string name)
{
 CheckUTF8(name);
 if (name.size() > 1024) throw Error("A package path is too long.");
 std::replace(name.begin(), name.end(), '\\', '/');
 if (name.empty() || name[0] == '/' || name.find(':') != std::string::npos)
  throw Error("Absolute and drive-qualified package paths are not allowed.");
 for (unsigned char c : name) if (c < 32 || c == 127) throw Error("Control characters in filenames are not allowed.");
 fs::path result;
 for (const auto &part : fs::path(name)) {
  auto component = part.string();
  if (component.empty() || component == ".") continue;
  if (component == ".." || component.size() > 240 || component.back() == '.' || component.back() == ' ')
   throw Error("The package contains an unsafe or ambiguous filename.");
  if (component == ".native-imports") throw Error("The package uses a reserved application directory.");
  result /= part;
 }
 if (result.empty()) throw Error("The package contains an empty filename.");
 return result;
}
std::string Key(const fs::path &path, const Options &options)
{
 auto value = path.generic_string();
 if (options.path_key) return options.path_key(value);
 for (unsigned char c : value) if (c >= 128)
  throw Error("This importer requires a platform Unicode normalizer for international archive filenames.");
 return Lower(value);
}
void SafeDirectories(const fs::path &root, const fs::path &relative)
{
 fs::path current = root;
 for (const auto &part : relative) {
  current /= part;
  std::error_code error;
  auto status = fs::symlink_status(current, error);
  if (error && error != std::errc::no_such_file_or_directory) throw Error("Could not inspect the import directory.");
  if (fs::is_symlink(status)) throw Error("An import directory is a symbolic link.");
  if (!fs::exists(status)) {
   if (!fs::create_directory(current)) throw Error("Could not create the import directory.");
  } else if (!fs::is_directory(status)) throw Error("A file is blocking an import directory.");
 }
}
void WriteAll(int fd, const char *data, size_t size)
{
 while (size) {
  ssize_t count = write(fd, data, size);
  if (count < 0 && errno == EINTR) continue;
  if (count <= 0) throw Error("Could not write imported content. Check available storage.");
  data += count;
  size -= static_cast<size_t>(count);
 }
}
void Sync(int fd) { if (fsync(fd) != 0) throw Error("Could not save imported content to storage."); }
void WriteJSON(const fs::path &path, const Json &value)
{
 auto temporary = path; temporary += ".next";
 FD file(open(temporary.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600));
 auto data = value.dump(2);
 WriteAll(file.value, data.data(), data.size());
 Sync(file.value);
 fs::rename(temporary, path);
}
void RenameExclusive(const fs::path &source, const fs::path &destination)
{
#ifdef __APPLE__
 int result = renameatx_np(AT_FDCWD, source.c_str(), AT_FDCWD, destination.c_str(), RENAME_EXCL);
#elif defined(__linux__)
 int result = static_cast<int>(syscall(SYS_renameat2, AT_FDCWD, source.c_str(), AT_FDCWD, destination.c_str(), RENAME_NOREPLACE));
#else
 int result = -1; errno = ENOTSUP;
#endif
 if (result != 0) throw Error(errno == EEXIST ? "Content with this name already exists. Nothing was replaced." : "Could not publish imported content.");
}
struct LockedRoot {
 fs::path root;
 std::unique_ptr<FD> lock;
 explicit LockedRoot(const fs::path &value) {
  if (!fs::is_directory(value)) throw Error("The game's content directory is unavailable.");
  root = fs::canonical(value);
  SafeDirectories(root, ".native-imports");
  lock = std::make_unique<FD>(open((root / ".native-imports/lock").c_str(), O_RDWR | O_CREAT | O_NOFOLLOW, 0600));
  if (flock(lock->value, LOCK_EX) != 0) throw Error("Could not lock the content installer.");
 }
};
bool TransactionName(const std::string &name)
{
 return name.size() == 12 && name.starts_with("stage-") &&
  std::all_of(name.begin() + 6, name.end(), [](unsigned char c) { return std::isalnum(c); });
}
bool DestinationAllowed(const fs::path &relative)
{
 static const std::set<std::string> roots{"save", "scenario", "newgrf", "baseset", "ai", "game"};
 return !relative.empty() && roots.contains(relative.begin()->string());
}
// Recovery moves only the transaction's new destinations to private quarantine.
// Original player files are never overwritten by publication or rollback.
void Rollback(const fs::path &root, const fs::path &stage, const Json &journal)
{
 const auto quarantine = fs::path(".native-imports/quarantine") / stage.filename();
 SafeDirectories(root, quarantine);
 for (const auto &item : journal.at("destinations")) {
  auto relative = SafePath(item.at("path").get<std::string>());
  if (!DestinationAllowed(relative)) throw Error("An import recovery record contains an invalid destination.");
  SafeDirectories(root, relative.parent_path());
  auto source = root / relative;
  if (!fs::exists(fs::symlink_status(source))) continue;
  if (fs::is_symlink(fs::symlink_status(source))) throw Error("An import recovery destination is a symbolic link.");
  struct stat status{};
  if (lstat(source.c_str(), &status) != 0) throw Error("Could not inspect an import recovery destination.");
  // Exclusive publication may fail because another file appeared. Only the
  // original staging inode belongs to this transaction; preserve other files.
  if (static_cast<uint64_t>(status.st_ino) != item.at("inode").get<uint64_t>() ||
      static_cast<uint64_t>(status.st_dev) != item.at("device").get<uint64_t>()) continue;
  SafeDirectories(root, quarantine / relative.parent_path());
  RenameExclusive(source, root / quarantine / relative);
 }
}
void RecoverLocked(const fs::path &root)
{
 for (const auto &entry : fs::directory_iterator(root / ".native-imports")) {
  if (!TransactionName(entry.path().filename().string())) continue;
  if (!entry.is_directory() || entry.is_symlink()) throw Error("An import staging directory is unsafe.");
  auto journal_path = entry.path() / "journal.json";
  if (fs::exists(journal_path)) {
   // Up to 10,000 long save names may legitimately need several MiB of journal.
   if (fs::is_symlink(fs::symlink_status(journal_path)) || fs::file_size(journal_path) > 16ULL * 1024 * 1024)
    throw Error("An import recovery record is unsafe.");
   Json journal;
   try { std::ifstream file(journal_path); file >> journal; }
   catch (...) { throw Error("An interrupted import has an unreadable recovery record. It was preserved for recovery."); }
   if (journal.at("state") != "complete") Rollback(root, entry.path(), journal);
  }
  fs::remove_all(entry.path());
 }
}
struct Budget {
 uint64_t input, bytes = 0, entries = 0;
 const Options &options;
 void Add(uint64_t count) {
  CheckCancelled(options);
  if (count > options.limits.expanded_bytes - std::min(bytes, options.limits.expanded_bytes))
   throw Error("The expanded package exceeds the import size limit.");
  bytes += count;
  if (input && (bytes / input > options.limits.expansion_ratio ||
      (bytes / input == options.limits.expansion_ratio && bytes % input)))
   throw Error("The package exceeds the permitted expansion ratio.");
 }
};
struct Item { fs::path file, relative; };
std::string ArchiveError(struct archive *reader)
{
 const char *message = archive_error_string(reader);
 return std::string("Cannot read this archive: ") + (message ? message : "unsupported or damaged data");
}
void CheckArchive(int status, struct archive *reader)
{
 if (status != ARCHIVE_OK) throw Error(ArchiveError(reader));
}
bool ArchiveExtension(const fs::path &path)
{
 auto extension = Lower(path.extension().string());
 return extension == ".zip" || extension == ".tar" || extension == ".gz" || extension == ".tgz";
}
void RejectExecutable(const fs::path &file)
{
 static const std::set<std::string> extensions{".exe", ".com", ".dll", ".dylib", ".so", ".framework", ".app", ".sh", ".bat", ".py", ".js", ".jar", ".dex", ".class", ".wasm"};
 for (const auto &part : file) if (extensions.contains(Lower(part.extension().string())))
  throw Error("Native executables and external script runtimes cannot be installed as game content.");
 std::ifstream stream(file, std::ios::binary);
 std::array<unsigned char, 4> magic{}; stream.read(reinterpret_cast<char *>(magic.data()), magic.size());
 if ((magic[0] == 'M' && magic[1] == 'Z') || (magic[0] == 0x7f && magic[1] == 'E' && magic[2] == 'L' && magic[3] == 'F') ||
     (magic[0] == 0xcf && magic[1] == 0xfa && magic[2] == 0xed && magic[3] == 0xfe) ||
     (magic[0] == 0xfe && magic[1] == 0xed && magic[2] == 0xfa && (magic[3] == 0xcf || magic[3] == 0xce)))
  throw Error("A native executable was disguised as a resource file.");
}
void Extract(const fs::path &source, const fs::path &output, Budget &budget,
             std::vector<Item> &items, unsigned depth)
{
 ScopedUTF8Locale locale; // No mutation of the engine thread's global locale.
 FD input(open(source.c_str(), O_RDONLY | O_NOFOLLOW));
 auto reader = std::unique_ptr<struct archive, decltype(&archive_read_free)>(archive_read_new(), archive_read_free);
 if (!reader) throw Error("Could not allocate an archive reader.");
 CheckArchive(archive_read_support_format_tar(reader.get()), reader.get());
 CheckArchive(archive_read_support_format_zip(reader.get()), reader.get());
 CheckArchive(archive_read_support_filter_none(reader.get()), reader.get());
 CheckArchive(archive_read_support_filter_gzip(reader.get()), reader.get());
 CheckArchive(archive_read_open_fd(reader.get(), input.value, CHUNK), reader.get());
 fs::create_directory(output);
 std::map<std::string, bool> seen;
 std::map<std::string, std::string> path_names;
 std::vector<Item> nested;
 struct archive_entry *entry = nullptr;
 std::array<char, CHUNK> buffer;
 for (;;) {
  CheckCancelled(budget.options);
  int status = archive_read_next_header(reader.get(), &entry);
  if (status == ARCHIVE_EOF) break;
  CheckArchive(status, reader.get());
  if (++budget.entries > budget.options.limits.entries) throw Error("The package contains too many entries.");
  if (archive_entry_is_encrypted(entry) != 0) throw Error("Encrypted packages are not supported.");
  if (archive_entry_symlink(entry) || archive_entry_hardlink(entry)) throw Error("Links in packages are not permitted.");
  auto type = archive_entry_filetype(entry);
  if (type != AE_IFREG && type != AE_IFDIR) throw Error("Only regular files and directories are permitted in packages.");
  auto raw_name = archive_entry_pathname_utf8(entry);
  if (!raw_name) throw Error("A package filename cannot be decoded as UTF-8.");
  std::string name(raw_name);
  // Tar creators commonly emit a harmless root directory header named './'.
  if ((name == "." || name == "./") && type == AE_IFDIR) continue;
  auto relative = SafePath(name);
  auto key = Key(relative, budget.options);
  for (auto part = relative; !part.empty(); part = part.parent_path()) {
   auto [found, inserted] = path_names.emplace(Key(part, budget.options), part.generic_string());
   if (!inserted && found->second != part.generic_string()) throw Error("The package contains ambiguous Unicode or case-colliding paths.");
  }
  if (!seen.emplace(key, type == AE_IFDIR).second) throw Error("The package contains duplicate or case-colliding filenames.");
  for (auto parent = relative.parent_path(); !parent.empty(); parent = parent.parent_path()) {
   auto found = seen.find(Key(parent, budget.options));
   if (found != seen.end() && !found->second) throw Error("A package file is also used as a directory.");
  }
  SafeDirectories(output, type == AE_IFDIR ? relative : relative.parent_path());
  if (type == AE_IFDIR) continue;
  if (archive_entry_size_is_set(entry) && archive_entry_size(entry) < 0) throw Error("A package file has an invalid size.");
  if (archive_entry_size_is_set(entry) && static_cast<uint64_t>(archive_entry_size(entry)) > budget.options.limits.expanded_bytes)
   throw Error("A package file exceeds the expanded size limit.");
  auto destination = output / relative;
  FD target(open(destination.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600));
  for (;;) {
   auto count = archive_read_data(reader.get(), buffer.data(), buffer.size());
   if (count < 0) throw Error(ArchiveError(reader.get()));
   if (!count) break;
   budget.Add(static_cast<uint64_t>(count));
   WriteAll(target.value, buffer.data(), static_cast<size_t>(count));
  }
  Sync(target.value);
  RejectExecutable(destination);
  Item item{destination, relative};
  if (ArchiveExtension(relative)) nested.push_back(item); else items.push_back(item);
 }
 CheckArchive(archive_read_close(reader.get()), reader.get());
 unsigned nested_index = 0;
 for (const auto &item : nested) {
  if (depth >= 1) throw Error("Only one nested package level is supported.");
  auto child = output.parent_path() / (output.filename().string() + "-nested-" + std::to_string(nested_index++));
  // Each nested archive gets its own extraction root and collision domain.
  Extract(item.file, child, budget, items, depth + 1);
 }
}
uint32_t FileKind(const fs::path &path)
{
 auto ext = Lower(path.extension().string());
 if (ext == ".sav" || ext == ".sv0" || ext == ".sv1" || ext == ".sv2" || ext == ".ss0" || ext == ".ss1") return Save;
 if (ext == ".scn") return Scenario;
 if (ext == ".png" || ext == ".bmp") return Heightmap;
 if (ext == ".grf") return NewGRF;
 if (ext == ".obg" || ext == ".obs" || ext == ".obm") return Baseset;
 return 0;
}
fs::path KindDirectory(uint32_t kind)
{
 switch (kind) {
 case Save: return "save";
 case Scenario: return "scenario";
 case Heightmap: return "scenario/heightmap";
 case NewGRF: return "newgrf";
 case Baseset: return "baseset";
 case AI: return "ai";
 case AILibrary: return "ai/library";
 case GameScript: return "game";
 case GameLibrary: return "game/library";
 default: throw Error("The package type could not be determined.");
 }
}
uint32_t ScriptKind(const Item &item)
{
 if (Lower(item.relative.filename().string()) != "info.nut" && Lower(item.relative.filename().string()) != "library.nut") return 0;
 if (fs::file_size(item.file) > 256 * 1024) throw Error("Script metadata exceeds the supported size.");
 std::ifstream input(item.file);
 std::string text((std::istreambuf_iterator<char>(input)), {});
 // This selects the original scanner only. It does not evaluate or trust script
 // metadata; OpenTTD's Squirrel scanner remains responsible for interpreting it.
 if (text.find("RegisterAI") != std::string::npos) return AI;
 if (text.find("RegisterGS") != std::string::npos) return GameScript;
 if (text.find("AILibrary") != std::string::npos) return AILibrary;
 if (text.find("GSLibrary") != std::string::npos) return GameLibrary;
 throw Error("Script metadata does not identify an OpenTTD AI, GameScript or library.");
}
struct Plan { fs::path source, destination; uint32_t kind; };
void MakePlans(const std::vector<Item> &items, const fs::path &stage, const fs::path &root,
               const std::string &id, std::vector<Plan> &plans)
{
 uint32_t package_kind = 0;
 for (const auto &item : items) {
  auto script_kind = ScriptKind(item);
  if (script_kind) {
   if (package_kind && package_kind != script_kind) throw Error("Import script packages separately from other content packages.");
   package_kind = script_kind;
  }
 }
 if (!package_kind) {
  for (const auto &item : items) if (FileKind(item.relative) == Baseset) package_kind = Baseset;
  if (!package_kind) for (const auto &item : items) if (FileKind(item.relative) == NewGRF) package_kind = NewGRF;
 }
 size_t number = 0;
 fs::path package = stage / "package";
 if (package_kind) fs::create_directory(package);
 std::set<fs::path> reserved;
 for (const auto &item : items) {
  auto kind = FileKind(item.relative);
  if (kind == Save || kind == Scenario || (!package_kind && kind == Heightmap)) {
   auto directory = KindDirectory(kind);
   SafeDirectories(root, directory);
   auto filename = item.relative.filename();
   auto destination = directory / filename;
   for (unsigned collision = 2; fs::exists(fs::symlink_status(root / destination)) || reserved.contains(destination); ++collision) {
    destination = directory / (filename.stem().string() + " (" + std::to_string(collision) + ")" + filename.extension().string());
    if (collision > 10000) throw Error("Too many files share this import name.");
   }
   reserved.insert(destination);
   auto staged = stage / ("file-" + std::to_string(number++));
   fs::rename(item.file, staged);
   plans.push_back({staged, destination, kind});
  } else if (package_kind) {
   SafeDirectories(package, item.relative.parent_path());
   auto destination = package / item.relative;
   if (fs::exists(fs::symlink_status(destination))) throw Error("Nested packages contain colliding file paths.");
   fs::rename(item.file, destination);
  }
 }
 if (package_kind) {
  auto directory = KindDirectory(package_kind);
  SafeDirectories(root, directory);
  plans.push_back({package, directory / ("import-" + id), package_kind});
 }
 if (plans.empty()) throw Error("No supported OpenTTD saves, scenarios, heightmaps, NewGRFs or content sets were found.");
}
uint64_t CopyInput(const fs::path &source, const fs::path &destination, const Options &options)
{
 FD input(open(source.c_str(), O_RDONLY | O_NOFOLLOW));
 struct stat status{};
 if (fstat(input.value, &status) || !S_ISREG(status.st_mode)) throw Error("Select a regular file to import.");
 if (status.st_size < 0 || static_cast<uint64_t>(status.st_size) > options.limits.input_bytes) throw Error("The selected file exceeds the import size limit.");
 FD output(open(destination.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600));
 std::array<char, CHUNK> buffer;
 uint64_t total = 0;
 for (;;) {
  CheckCancelled(options);
  auto count = read(input.value, buffer.data(), buffer.size());
  if (count < 0 && errno == EINTR) continue;
  if (count < 0) throw Error("Could not read the selected file.");
  if (!count) break;
  total += static_cast<uint64_t>(count);
  if (total > options.limits.input_bytes) throw Error("The selected file exceeds the import size limit.");
  WriteAll(output.value, buffer.data(), static_cast<size_t>(count));
 }
 Sync(output.value);
 return total;
}
}

void Recover(const std::filesystem::path &game_root)
{
 try { LockedRoot locked(game_root); RecoverLocked(locked.root); }
 catch (const Error &) { throw; }
 catch (const std::exception &) { throw Error("An interrupted import could not be recovered. Its files were preserved."); }
}
Result Import(const std::filesystem::path &source, const std::filesystem::path &game_root, const Options &options)
{
 LockedRoot locked(game_root);
 RecoverLocked(locked.root);
 auto name = SafePath(source.filename().string()).filename();
 std::string pattern = (locked.root / ".native-imports/stage-XXXXXX").string();
 if (!mkdtemp(pattern.data())) throw Error("Could not create a private import staging directory.");
 fs::path stage(pattern);
 Json journal{{"state", "preparing"}, {"destinations", Json::array()}};
 bool committed = false;
 try {
  auto copied = stage / "input";
  uint64_t input_bytes = CopyInput(source, copied, options);
  Budget budget{input_bytes, 0, 0, options};
  std::vector<Item> items;
  if (ArchiveExtension(name)) Extract(copied, stage / "expanded", budget, items, 0);
  else {
   RejectExecutable(copied);
   budget.Add(input_bytes);
   items.push_back({copied, name});
  }
  std::vector<Plan> plans;
  auto id = stage.filename().string().substr(6);
  MakePlans(items, stage, locked.root, id, plans);
  CheckCancelled(options);
  // Journal all destinations before any becomes visible to original scanners.
  for (const auto &plan : plans) {
   struct stat status{};
   if (lstat(plan.source.c_str(), &status) != 0) throw Error("Could not inspect staged content.");
   journal["destinations"].push_back({{"path", plan.destination.generic_string()},
    {"inode", static_cast<uint64_t>(status.st_ino)}, {"device", static_cast<uint64_t>(status.st_dev)}});
  }
  journal["state"] = "publishing";
  WriteJSON(stage / "journal.json", journal);
  Result result{name.string(), 0, budget.bytes, {}, false};
  for (const auto &plan : plans) {
   RenameExclusive(plan.source, locked.root / plan.destination);
   result.kinds |= plan.kind;
   result.installed_paths.push_back(plan.destination.generic_string());
  }
  result.includes_scripts = result.kinds & (AI | AILibrary | GameScript | GameLibrary);
  journal["state"] = "complete";
  WriteJSON(stage / "journal.json", journal);
  committed = true;
  fs::remove_all(stage);
  return result;
 } catch (...) {
  auto failure = std::current_exception();
  try {
   if (!committed && (journal["state"] == "publishing" || journal["state"] == "complete")) Rollback(locked.root, stage, journal);
   fs::remove_all(stage);
  } catch (...) {
   throw Error("The import was interrupted during recovery. Its staged files were preserved; restart before importing again.");
  }
  try { std::rethrow_exception(failure); }
  catch (const Error &) { throw; }
  catch (const std::exception &) { throw Error("Could not install this package. Existing content was preserved."); }
 }
}
}
