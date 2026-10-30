#!/usr/bin/env python3
"""Exercise the real Apple resource migration, including player-file preservation."""
from pathlib import Path
import subprocess, tempfile, json, os
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#import <Foundation/Foundation.h>
#include "ManagedResources.h"
#include <cstdlib>
static int passed=0;
static void Check(BOOL ok,NSString *message){if(!ok){fprintf(stderr,"FAIL: %s\n",message.UTF8String);exit(1);}++passed;}
int main(int argc,char **argv){@autoreleasepool{
 NSFileManager *fm=NSFileManager.defaultManager;
 NSURL *temp=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]] isDirectory:YES];
 NSURL *bundle=[temp URLByAppendingPathComponent:@"bundle"],*root=[temp URLByAppendingPathComponent:@"root"];
 for(NSURL *p in @[bundle,root])[fm createDirectoryAtURL:[p URLByAppendingPathComponent:@"baseset"] withIntermediateDirectories:YES attributes:nil error:nil];
 NSURL *replacement=[bundle URLByAppendingPathComponent:@"baseset/classic-menu.dat"],*target=[root URLByAppendingPathComponent:@"baseset/opntitle.dat"];
 NSData *classic=[NSData dataWithContentsOfFile:[NSString stringWithUTF8String:argv[2]]];
 NSData *old=[NSData dataWithContentsOfFile:[NSString stringWithUTF8String:argv[3]]];
 [classic writeToURL:replacement atomically:YES];[old writeToURL:target atomically:YES];NSError *error=nil;
 Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:target]isEqual:classic],@"Known bundled scene migrates");
 NSNumber *inode=[fm attributesOfItemAtPath:target.path error:nil][NSFileSystemFileNumber];
 Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[inode isEqual:[fm attributesOfItemAtPath:target.path error:nil][NSFileSystemFileNumber]],@"Repeat update does not rewrite scene");
 NSData *custom=[@"Player supplied title" dataUsingEncoding:NSUTF8StringEncoding];[custom writeToURL:target atomically:YES];
 Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:target]isEqual:custom],@"Custom scene is preserved");
 [fm removeItemAtURL:target error:nil];Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:target]isEqual:classic],@"Missing title installs verified scene");
 [custom writeToURL:replacement atomically:YES];[old writeToURL:target atomically:YES];
 Check(!InstallClassicMenuIfUnmodified(bundle,root,&error)&&error&&[[NSData dataWithContentsOfURL:target]isEqual:old],@"Damaged bundled scene fails without replacing destination");
 [classic writeToURL:replacement atomically:YES];[fm removeItemAtURL:target error:nil];NSURL *outside=[temp URLByAppendingPathComponent:@"player-file"];
 [custom writeToURL:outside atomically:YES];[fm createSymbolicLinkAtPath:target.path withDestinationPath:outside.path error:nil];
 Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[[fm attributesOfItemAtPath:target.path error:nil][NSFileType]isEqual:NSFileTypeSymbolicLink]&&[[NSData dataWithContentsOfURL:outside]isEqual:custom],@"Custom symlink and its target remain unchanged");
 NSURL *base=[root URLByAppendingPathComponent:@"baseset"],*outsideBase=[temp URLByAppendingPathComponent:@"player-directory"];
 [fm removeItemAtURL:base error:nil];[fm createDirectoryAtURL:outsideBase withIntermediateDirectories:YES attributes:nil error:nil];
 NSURL *outsideTitle=[outsideBase URLByAppendingPathComponent:@"opntitle.dat"];[old writeToURL:outsideTitle atomically:YES];
 [fm createSymbolicLinkAtPath:base.path withDestinationPath:outsideBase.path error:nil];
 Check(InstallClassicMenuIfUnmodified(bundle,root,&error)&&[[fm attributesOfItemAtPath:base.path error:nil][NSFileType]isEqual:NSFileTypeSymbolicLink]&&[[NSData dataWithContentsOfURL:outsideTitle]isEqual:old],@"Symlinked parent directory and its original title are preserved");
 printf("%d managed-resource checks passed\n",passed);
}return 0;}
'''
with tempfile.TemporaryDirectory(prefix='openttd-resource-tests-') as temp:
    folder=Path(temp);source=folder/'tests.mm';source.write_text(SOURCE);executable=folder/'tests'
    command=['xcrun','clang++','-std=c++20','-fobjc-arc','-fsanitize=address,undefined','-g','-I',str(ROOT/'native/apple'),str(source),str(ROOT/'native/apple/ManagedResources.mm'),'-framework','Foundation','-o',str(executable)]
    subprocess.run(command,check=True)
    result=subprocess.run([str(executable),str(folder/'fixtures'),str(ROOT/'native/apple/ClassicMenu/classic-menu.dat'),str(ROOT/'build/ipad-resources/baseset/opntitle.dat')],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},text=True,capture_output=True,check=True)
    print(result.stdout.strip())
    (ROOT/'evidence/managed-resource-tests.json').write_text(json.dumps({'checks':7,'result':'passed','sanitizers':['AddressSanitizer','UndefinedBehaviorSanitizer'],'scope':'Known-scene migration, idempotence, custom/missing files, corrupt bundle, destination and parent symlink preservation','stdout':result.stdout},indent=2))
