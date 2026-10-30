#import <UIKit/UIKit.h>
void ConfigureNativeContentImport(UIViewController *controller, NSURL *gameRoot);
BOOL RecoverNativeContentImports(NSURL *gameRoot, NSError **error);
// Called on the engine owner thread by original widgets; presentation is queued.
void OpenNativeContentImport();
