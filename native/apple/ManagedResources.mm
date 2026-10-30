#include "ManagedResources.h"
#include <CommonCrypto/CommonDigest.h>

static NSString *Digest(NSData *data){
 unsigned char bytes[CC_SHA256_DIGEST_LENGTH];CC_SHA256(data.bytes,(CC_LONG)data.length,bytes);
 NSMutableString *result=[NSMutableString stringWithCapacity:64];for(unsigned char byte:bytes)[result appendFormat:@"%02x",byte];return result;
}
BOOL InstallClassicMenuIfUnmodified(NSURL *bundleData,NSURL *root,NSError **error){
 NSURL *source=[bundleData URLByAppendingPathComponent:@"baseset/classic-menu.dat"];
 NSData *replacement=[NSData dataWithContentsOfURL:source options:0 error:error];if(!replacement)return NO;
 if(![Digest(replacement) isEqualToString:@"1645d6bd627df06986b1884c57f1e328f3ab606aa32549ed88a9220b1b1230fa"]){
  if(error)*error=[NSError errorWithDomain:@"OpenTTDResources" code:2 userInfo:@{NSLocalizedDescriptionKey:@"The bundled classic opening scene could not be verified."}];return NO;
 }
 NSURL *destination=[root URLByAppendingPathComponent:@"baseset/opntitle.dat"];
 NSFileManager *fm=NSFileManager.defaultManager;
 NSDictionary *baseAttributes=[fm attributesOfItemAtPath:[root URLByAppendingPathComponent:@"baseset"].path error:nil];
 if(baseAttributes&&![baseAttributes[NSFileType] isEqual:NSFileTypeDirectory])return YES;
 NSDictionary *attributes=[fm attributesOfItemAtPath:destination.path error:nil];
 if(attributes){
  // Preserve user-supplied scenes and symbolic links. Never follow a custom
  // title path merely because the application has gained an updated resource.
  if(![attributes[NSFileType] isEqual:NSFileTypeRegular]||[attributes[NSFileSize] unsignedLongLongValue]>16*1024*1024)return YES;
  NSData *existing=[NSData dataWithContentsOfURL:destination options:0 error:error];if(!existing)return NO;
  if(![Digest(existing) isEqualToString:@"ebb39b9b14ec756594bd63050e746787f5770cb970219d41169e8d4e8183732d"])return YES;
 }
 return [replacement writeToURL:destination options:NSDataWritingAtomic error:error];
}
