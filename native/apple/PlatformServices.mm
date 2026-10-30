#import <UIKit/UIKit.h>
// GPL-2.0: iOS platform services; gameplay stays in the original engine.
#include "stdafx.h"
#include "fios.h"
#include "crashlog.h"
#include "survey.h"
#include "3rdparty/nlohmann/json.hpp"
#include "thread.h"
#include <sys/mount.h>
#include <pthread.h>

bool FiosIsRoot(const std::string &path){return path=="/";}
void FiosGetDrives(FileList &){}
std::optional<uint64_t> FiosGetDiskFreeSpace(const std::string &path){struct statfs s;if(statfs(path.c_str(),&s)==0)return uint64_t(s.f_bsize)*s.f_bavail;return std::nullopt;}
bool FiosIsHiddenFile(const std::filesystem::path &path){return path.filename().string().starts_with(".");}
void SetCurrentThreadName(const std::string &name){pthread_setname_np(name.c_str());}
void ShowInfoI(std::string_view text){fprintf(stderr,"%.*s\n",static_cast<int>(text.size()),text.data());}
void ShowOSErrorBox(std::string_view text,bool){fprintf(stderr,"OpenTTD error: %.*s\n",static_cast<int>(text.size()),text.data());}
std::optional<std::string> GetCurrentLocale(const char *){return std::string("en_GB.UTF-8");}
std::optional<std::string> GetClipboardContents(){return std::nullopt;}
void OSOpenBrowser(const std::string &url){NSString *s=[[NSString alloc]initWithBytes:url.data() length:url.size() encoding:NSUTF8StringEncoding];dispatch_async(dispatch_get_main_queue(),^{NSURL *u=[NSURL URLWithString:s];if(u&&([u.scheme isEqualToString:@"https"]||[u.scheme isEqualToString:@"http"]))[[UIApplication sharedApplication]openURL:u options:@{} completionHandler:nil];});}
void SurveyOS(nlohmann::json &json){json["name"]="iOS";json["version"]=std::string([NSProcessInfo.processInfo.operatingSystemVersionString UTF8String]);}
void CrashLog::InitialiseCrashLog(){} // iOS generates platform crash reports; no desktop signal UI.
void CrashLog::InitThread(){}
