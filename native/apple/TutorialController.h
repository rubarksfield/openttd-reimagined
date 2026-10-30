// GPL-2.0: Optional native guidance; never issues simulation commands.
#pragma once
void ShowNativeTouchTutorial();
#ifdef __OBJC__
@class UIViewController;
void ConfigureNativeTouchTutorial(UIViewController *presenter);
void OfferNativeTouchTutorialIfNeeded();
#endif
