// GPL-2.0. Preferences only; OpenTTD renders the original game windows.
#import <Foundation/Foundation.h>
#include "TutorialController.h"
#include "EngineBridge.h"
void ConfigureNativeTouchTutorial(UIViewController *){}
void ShowNativeTouchTutorial(){
 NSString *path=[NSBundle.mainBundle pathForResource:@"first-steps" ofType:@"json"];
 if(path)OTTDShowTutorial(path.UTF8String);
}
void OfferNativeTouchTutorialIfNeeded(){
 if([NSUserDefaults.standardUserDefaults boolForKey:@"OpenTTD.FirstSteps.Offered.v2"])return;
 [NSUserDefaults.standardUserDefaults setBool:YES forKey:@"OpenTTD.FirstSteps.Offered.v2"];
 ShowNativeTouchTutorial();
}
