#!/usr/bin/env python3
"""Exercise the native bundled-coaching update against the exact shipped v1 files."""
from pathlib import Path
import json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#import <Foundation/Foundation.h>
#include "ManagedResources.h"
#include <cstdlib>
static int passed=0;
static void Check(BOOL ok,const char *message){if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}++passed;}
int main(int argc,char **argv){@autoreleasepool{
 NSFileManager *fm=NSFileManager.defaultManager;
 NSURL *temp=[NSURL fileURLWithPath:@(argv[1])],*current=[NSURL fileURLWithPath:@(argv[2])],*legacy=[NSURL fileURLWithPath:@(argv[3])];
 NSURL *root=[temp URLByAppendingPathComponent:@"root"],*bundle=[temp URLByAppendingPathComponent:@"bundle"];
 for(NSURL *p in @[root,bundle])[fm createDirectoryAtURL:[p URLByAppendingPathComponent:@"game"] withIntermediateDirectories:YES attributes:nil error:nil];
 [fm copyItemAtURL:current toURL:[bundle URLByAppendingPathComponent:@"game/TouchFirstRoute"] error:nil];
 NSURL *package=[root URLByAppendingPathComponent:@"game/TouchFirstRoute"];
 NSURL *main=[package URLByAppendingPathComponent:@"main.nut"],*lang=[package URLByAppendingPathComponent:@"lang/english.txt"];
 NSData *oldMain=[NSData dataWithContentsOfURL:[legacy URLByAppendingPathComponent:@"main.nut"]],*oldLang=[NSData dataWithContentsOfURL:[legacy URLByAppendingPathComponent:@"lang/english.txt"]];
 NSData *newMain=[NSData dataWithContentsOfURL:[current URLByAppendingPathComponent:@"main.nut"]],*newLang=[NSData dataWithContentsOfURL:[current URLByAppendingPathComponent:@"lang/english.txt"]];
 NSData *custom=[@"Player modified file" dataUsingEncoding:NSUTF8StringEncoding];
 void (^reset)(void)=^{[fm removeItemAtURL:package error:nil];[fm copyItemAtURL:legacy toURL:package error:nil];};
 reset();NSURL *save=[root URLByAppendingPathComponent:@"player.sav"];[custom writeToURL:save atomically:YES];NSError *error=nil;
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:newMain]&&[[NSData dataWithContentsOfURL:lang]isEqual:newLang],"exact shipped files upgrade");
 Check([[NSData dataWithContentsOfURL:save]isEqual:custom],"player save remains intact");
 NSNumber *inode=[fm attributesOfItemAtPath:main.path error:nil][NSFileSystemFileNumber];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[inode isEqual:[fm attributesOfItemAtPath:main.path error:nil][NSFileSystemFileNumber]],"repeat does not rewrite");
 reset();[custom writeToURL:main atomically:YES];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:custom]&&[[NSData dataWithContentsOfURL:lang]isEqual:oldLang],"modified main preserves whole package");
 reset();[custom writeToURL:lang atomically:YES];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:oldMain]&&[[NSData dataWithContentsOfURL:lang]isEqual:custom],"modified translation preserves whole package");
 reset();[custom writeToURL:[package URLByAppendingPathComponent:@"info.nut"] atomically:YES];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:oldMain]&&[[NSData dataWithContentsOfURL:lang]isEqual:oldLang],"modified metadata preserves whole package");
 reset();[newLang writeToURL:lang atomically:YES];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:newMain],"interrupted update resumes");
 reset();NSURL *outside=[temp URLByAppendingPathComponent:@"outside-main"];[oldMain writeToURL:outside atomically:YES];[fm removeItemAtURL:main error:nil];[fm createSymbolicLinkAtPath:main.path withDestinationPath:outside.path error:nil];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[fm attributesOfItemAtPath:main.path error:nil][NSFileType]isEqual:NSFileTypeSymbolicLink]&&[[NSData dataWithContentsOfURL:outside]isEqual:oldMain]&&[[NSData dataWithContentsOfURL:lang]isEqual:oldLang],"symlinked script and target preserved");
 reset();NSURL *outsideDir=[temp URLByAppendingPathComponent:@"outside-language"];[fm moveItemAtURL:[package URLByAppendingPathComponent:@"lang"] toURL:outsideDir error:nil];[fm createSymbolicLinkAtPath:[package URLByAppendingPathComponent:@"lang"].path withDestinationPath:outsideDir.path error:nil];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:oldMain]&&[[NSData dataWithContentsOfURL:[outsideDir URLByAppendingPathComponent:@"english.txt"]]isEqual:oldLang],"symlinked parent preserved");
 reset();[fm removeItemAtURL:lang error:nil];
 Check(InstallTutorialIfUnmodified(bundle,root,&error)&&[[NSData dataWithContentsOfURL:main]isEqual:oldMain],"incomplete custom package left intact");
 printf("%d native tutorial update checks passed\n",passed);
}}
'''
with tempfile.TemporaryDirectory(prefix='tutorial-resource-update-') as temp:
    temp=Path(temp);source=temp/'test.mm';source.write_text(SOURCE);executable=temp/'test'
    subprocess.run(['xcrun','clang++','-std=c++20','-fobjc-arc','-fsanitize=address,undefined','-g','-I',str(ROOT/'native/apple'),str(source),str(ROOT/'native/apple/ManagedResources.mm'),'-framework','Foundation','-o',str(executable)],check=True)
    result=subprocess.run([str(executable),str(temp),str(ROOT/'content/game/TouchFirstRoute'),str(ROOT/'script/fixtures/tutorial-v1')],capture_output=True,text=True,check=True)
    print(result.stdout.strip());(ROOT/'evidence/tutorial-resource-update-tests.json').write_text(json.dumps({'result':'passed','sanitizers':['address','undefined'],'output':result.stdout.strip()},indent=2))
