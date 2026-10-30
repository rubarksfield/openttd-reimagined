// GPL-2.0. Native document grants and presentation; shared C++ owns installation.
#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include "ContentImportController.h"
#include "ContentImporter.h"
#include "ContentPathKey.h"
#include "EngineBridge.h"
#include <atomic>
#include <memory>

@interface OTTDContentImportController : NSObject<UIDocumentPickerDelegate>
@property(nonatomic,weak)UIViewController *presenter;
@property(nonatomic,strong)NSURL *gameRoot;
@property(nonatomic)BOOL busy;
-(void)open;
@end
static OTTDContentImportController *importController;

BOOL RecoverNativeContentImports(NSURL *gameRoot, NSError **error)
{
 try { ottd::content::Recover(gameRoot.fileSystemRepresentation); return YES; }
 catch (const std::exception &failure) {
  if (error) *error = [NSError errorWithDomain:@"OpenTTDContentImport" code:1
   userInfo:@{NSLocalizedDescriptionKey:[NSString stringWithUTF8String:failure.what()] ?: @"Import recovery failed. Its files were preserved."}];
  return NO;
 }
}
void ConfigureNativeContentImport(UIViewController *controller, NSURL *gameRoot)
{
 NSCAssert(NSThread.isMainThread,@"Native import configuration must run on the main thread");
 if (!importController) importController = [OTTDContentImportController new];
 importController.presenter = controller;
 importController.gameRoot = gameRoot;
}
void OpenNativeContentImport()
{
 dispatch_async(dispatch_get_main_queue(), ^{ [importController open]; });
}
@implementation OTTDContentImportController
-(void)open
{
 if (self.busy || !self.presenter || self.presenter.presentedViewController) return;
 self.busy = YES;
 [self.presenter.view endEditing:YES];
 self.presenter.view.accessibilityElementsHidden = YES;
 UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc]
  initForOpeningContentTypes:@[UTTypeData, UTTypeArchive] asCopy:NO];
 picker.delegate = self;
 picker.allowsMultipleSelection = YES;
 [self.presenter presentViewController:picker animated:YES completion:^{UIAccessibilityPostNotification(UIAccessibilityScreenChangedNotification,nil);}];
}
-(void)documentPickerWasCancelled:(UIDocumentPickerViewController*)controller
{
 self.busy = NO;
 self.presenter.view.accessibilityElementsHidden = NO;
 UIAccessibilityPostNotification(UIAccessibilityScreenChangedNotification,nil);
}
-(void)documentPicker:(UIDocumentPickerViewController*)controller didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls
{
 if (!urls.count) { self.busy = NO; self.presenter.view.accessibilityElementsHidden = NO; return; }
 NSArray<NSURL*> *selected = [urls copy];
 NSURL *root = self.gameRoot;
 auto cancelled = std::make_shared<std::atomic<bool>>(false);
 UIAlertController *progress = [UIAlertController alertControllerWithTitle:@"Importing content…"
  message:@"Checking the selected files and installing supported OpenTTD content."
  preferredStyle:UIAlertControllerStyleAlert];
 [progress addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:^(UIAlertAction *action){cancelled->store(true);}]];
 void (^beginWork)(void) = ^{
  dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
  @autoreleasepool {
   NSMutableArray<NSString*> *failures = [NSMutableArray array];
   __block NSUInteger imported = 0;
   __block uint32_t kinds = 0;
   for (NSURL *url in selected) {
    if (cancelled->load()) break;
    BOOL scoped = [url startAccessingSecurityScopedResource];
    __block NSString *failure = nil;
    NSError *coordinationError = nil;
    NSFileCoordinator *coordinator = [[NSFileCoordinator alloc]initWithFilePresenter:nil];
    [coordinator coordinateReadingItemAtURL:url options:NSFileCoordinatorReadingWithoutChanges error:&coordinationError byAccessor:^(NSURL *coordinatedURL){
     try {
      ottd::content::Options options;
      options.cancelled = [cancelled]{return cancelled->load();};
      options.path_key = NativeContentPathKey;
      auto result = ottd::content::Import(coordinatedURL.fileSystemRepresentation,root.fileSystemRepresentation,options);
      kinds |= result.kinds;
      ++imported;
     } catch (const std::exception &error) { failure = [NSString stringWithUTF8String:error.what()] ?: @"This file could not be imported."; }
    }];
    if (scoped) [url stopAccessingSecurityScopedResource];
    if (coordinationError) failure = coordinationError.localizedDescription;
    if (failure) [failures addObject:[NSString stringWithFormat:@"%@: %@",url.lastPathComponent,failure]];
    // The shared importer made its own bounded snapshot. Never remove or modify
    // the document-provider original, even when the user selected our own Files.
   }
   // Scanner changes always execute on OpenTTD's owner thread after publication.
   // Also clear stale scans following a failed batch's recovery.
   OTTDContentChanged(kinds ? kinds : 511);
   NSString *message = imported ? [NSString stringWithFormat:@"Imported %lu %@. OpenTTD checks compatibility when content is loaded.",
    (unsigned long)imported,imported==1?@"file":@"files"] : @"Nothing was installed.";
   if (cancelled->load()) message = [message stringByAppendingString:@"\n\nImport was cancelled. Completed imports were kept."];
   if (failures.count) message = [message stringByAppendingFormat:@"\n\n%@",[failures componentsJoinedByString:@"\n\n"]];
   dispatch_async(dispatch_get_main_queue(), ^{
    self.busy = NO;
    void (^showResult)(void) = ^{
     NSString *title = cancelled->load()?@"Import cancelled":(!imported&&failures.count)?@"Couldn’t import content":@"Content imported";
     UIAlertController *result = [UIAlertController alertControllerWithTitle:title
      message:message preferredStyle:UIAlertControllerStyleAlert];
     [result addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){
      self.presenter.view.accessibilityElementsHidden = NO;
      UIAccessibilityPostNotification(UIAccessibilityScreenChangedNotification,nil);
     }]];
     [self.presenter presentViewController:result animated:YES completion:nil];
    };
    if (self.presenter.presentedViewController == progress) [progress dismissViewControllerAnimated:YES completion:showResult];
    else if (!self.presenter.presentedViewController) showResult();
   });
  }
  });
 };
 // Start work only after progress presentation completes, including very fast
 // failures. It must never finish behind the disappearing Files picker.
 void (^showProgress)(void) = ^{[self.presenter presentViewController:progress animated:YES completion:beginWork];};
 dispatch_async(dispatch_get_main_queue(), ^{
  if (controller.isBeingDismissed && controller.transitionCoordinator) {
   [controller.transitionCoordinator animateAlongsideTransition:nil completion:^(id<UIViewControllerTransitionCoordinatorContext> context){showProgress();}];
  } else if (controller.presentingViewController) {
   [controller dismissViewControllerAnimated:YES completion:showProgress];
  } else showProgress();
 });
}
@end
