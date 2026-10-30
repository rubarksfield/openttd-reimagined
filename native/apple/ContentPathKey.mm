#import <Foundation/Foundation.h>
#include "ContentPathKey.h"
#include <stdexcept>
std::string NativeContentPathKey(const std::string &path)
{
 @autoreleasepool {
  NSString *name = [[NSString alloc] initWithBytes:path.data() length:path.size() encoding:NSUTF8StringEncoding];
  if (!name) throw std::runtime_error("Invalid UTF-8 package path");
  NSString *key = [[name precomposedStringWithCanonicalMapping]
   stringByFoldingWithOptions:NSCaseInsensitiveSearch locale:[NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"]];
  return [[key precomposedStringWithCanonicalMapping] UTF8String];
 }
}
