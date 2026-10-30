// GPL-2.0: UIKit/Metal host for the original OpenTTD engine.
#import <UIKit/UIKit.h>
#import <MetalKit/MetalKit.h>
#include "EngineBridge.h"
#include "ContentImportController.h"
#include "TutorialController.h"
#include "ManagedResources.h"

@class OTTDGameView;
@protocol OTTDScrollAccess<NSObject>
-(BOOL)scrollAccessible:(UIAccessibilityScrollDirection)direction atGamePoint:(CGPoint)point;
@end
@interface OTTDAccessibleWidget:UIAccessibilityElement
@property(nonatomic)CGPoint gamePoint;
@end
@implementation OTTDAccessibleWidget
-(BOOL)accessibilityActivate{if(self.accessibilityTraits&UIAccessibilityTraitStaticText)return NO;OTTDTouch(0,self.gamePoint.x,self.gamePoint.y);OTTDTouch(2,self.gamePoint.x,self.gamePoint.y);return YES;}
-(BOOL)accessibilityScroll:(UIAccessibilityScrollDirection)direction{return [(id<OTTDScrollAccess>)self.accessibilityContainer scrollAccessible:direction atGamePoint:self.gamePoint];}
@end

@interface OTTDKeyboardInput:UIView<UIKeyInput>
@property(nonatomic,strong)UIView *replacementInputView;
@end
@implementation OTTDKeyboardInput
-(BOOL)canBecomeFirstResponder{return YES;}
-(BOOL)hasText{return YES;}
-(UIView*)inputView{return self.replacementInputView;}
-(void)insertText:(NSString*)text{if([text isEqualToString:@"\n"]){OTTDKey(13,nullptr);[self resignFirstResponder];}else OTTDKey(0,text.UTF8String);}
-(void)deleteBackward{OTTDKey(2,nullptr);}
-(UIKeyboardType)keyboardType{return UIKeyboardTypeDefault;}
-(UITextAutocorrectionType)autocorrectionType{return UITextAutocorrectionTypeNo;}
-(UITextAutocapitalizationType)autocapitalizationType{return UITextAutocapitalizationTypeNone;}
@end

@interface OTTDGameView:MTKView<MTKViewDelegate,UIGestureRecognizerDelegate,OTTDScrollAccess>{
 NSLock *_frameLock;NSData *_latestPixels;NSData *_latestMetadata;int _frameWidth,_frameHeight;
 id<MTLCommandQueue> _queue;id<MTLRenderPipelineState> _pipeline;id<MTLTexture> _texture;
 OTTDKeyboardInput *_textInput;UIView *_hiddenKeyboard,*_dialogScrollIndicator;int _keyboardMode;UILabel *_loading;NSArray *_widgetDescriptions;NSMutableDictionary<NSString*,OTTDAccessibleWidget*> *_accessibleWidgets;OTTDAccessibleWidget *_worldElement;BOOL _started;CGFloat _pinchRemainder;CGSize _lastSize,_accessibilitySize;CGPoint _twoFingerAnchor;
}
-(void)acceptPixels:(const void*)pixels width:(int)width height:(int)height metadata:(const char*)metadata;
-(void)setKeyboardMode:(int)mode;
@end
static void Frame(void *context,const void *pixels,int w,int h,const char *metadata){@autoreleasepool{[(__bridge OTTDGameView*)context acceptPixels:pixels width:w height:h metadata:metadata];}}
static void Keyboard(void *context,int mode){dispatch_async(dispatch_get_main_queue(),^{[(__bridge OTTDGameView*)context setKeyboardMode:mode];});}

// Only install missing, trusted bundle resources. Existing player files and
// settings are never replaced by an application update.
static BOOL InstallMissingResources(NSFileManager *fm, NSURL *bundleData, NSURL *root, NSError **error){
 __block NSError *enumerationError=nil;
 NSDirectoryEnumerator<NSURL*> *files=[fm enumeratorAtURL:bundleData includingPropertiesForKeys:@[NSURLIsRegularFileKey] options:0 errorHandler:^BOOL(NSURL *url,NSError *failure){enumerationError=failure;return NO;}];
 if(!files){if(error)*error=[NSError errorWithDomain:@"OpenTTDResources" code:1 userInfo:@{NSLocalizedDescriptionKey:@"Bundled game resources are missing."}];return NO;}
 for(NSURL *source in files){
  NSNumber *regular=nil;if(![source getResourceValue:&regular forKey:NSURLIsRegularFileKey error:error])return NO;
  if(!regular.boolValue)continue;
  NSString *relative=[source.path substringFromIndex:bundleData.path.length+1];
  NSURL *destination=[root URLByAppendingPathComponent:relative];
  if([fm fileExistsAtPath:destination.path])continue;
  if(![fm createDirectoryAtURL:destination.URLByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:error])return NO;
  NSURL *temporary=[destination.URLByDeletingLastPathComponent URLByAppendingPathComponent:[@".install-" stringByAppendingString:NSUUID.UUID.UUIDString]];
  if(![fm copyItemAtURL:source toURL:temporary error:error]||![fm moveItemAtURL:temporary toURL:destination error:error]){
   [fm removeItemAtURL:temporary error:nil];return NO;
  }
 }
 if(enumerationError){if(error)*error=enumerationError;return NO;}
 return YES;
}
@implementation OTTDGameView
-(instancetype)initWithFrame:(CGRect)frame{
 self=[super initWithFrame:frame device:MTLCreateSystemDefaultDevice()];if(!self)return nil;
 _frameLock=[NSLock new];_queue=[self.device newCommandQueue];_accessibleWidgets=[NSMutableDictionary dictionary];
 _textInput=[[OTTDKeyboardInput alloc]initWithFrame:CGRectMake(-10,-10,1,1)];_textInput.accessibilityElementsHidden=YES;[self addSubview:_textInput];
 _hiddenKeyboard=[[UIView alloc]initWithFrame:CGRectZero];
 _dialogScrollIndicator=[UIView new];_dialogScrollIndicator.backgroundColor=[UIColor colorWithWhite:1 alpha:0.7];_dialogScrollIndicator.layer.cornerRadius=1.5;_dialogScrollIndicator.userInteractionEnabled=NO;_dialogScrollIndicator.isAccessibilityElement=NO;_dialogScrollIndicator.hidden=YES;[self addSubview:_dialogScrollIndicator];
 _textInput.inputAssistantItem.leadingBarButtonGroups=@[];_textInput.inputAssistantItem.trailingBarButtonGroups=@[];
 self.delegate=self;self.preferredFramesPerSecond=60;self.colorPixelFormat=MTLPixelFormatBGRA8Unorm;
 self.userInteractionEnabled=YES;self.multipleTouchEnabled=YES;self.accessibilityIdentifier=@"openttd.surface";
 self.backgroundColor=UIColor.blackColor;self.isAccessibilityElement=NO;self.accessibilityElementsHidden=NO;
 NSString *shader=@"#include <metal_stdlib>\nusing namespace metal; struct V {float4 p [[position]];float2 uv;}; vertex V vs(uint i [[vertex_id]]){float2 p[4]={float2(-1,-1),float2(1,-1),float2(-1,1),float2(1,1)};V o;o.p=float4(p[i],0,1);o.uv=float2((p[i].x+1)*0.5,(1-p[i].y)*0.5);return o;} fragment float4 fs(V v [[stage_in]],texture2d<float> tex [[texture(0)]]){constexpr sampler s(filter::nearest,address::clamp_to_edge);return float4(tex.sample(s,v.uv).rgb,1);}";
 NSError *error=nil;id<MTLLibrary> library=[self.device newLibraryWithSource:shader options:nil error:&error];
 MTLRenderPipelineDescriptor *descriptor=[MTLRenderPipelineDescriptor new];descriptor.vertexFunction=[library newFunctionWithName:@"vs"];descriptor.fragmentFunction=[library newFunctionWithName:@"fs"];descriptor.colorAttachments[0].pixelFormat=self.colorPixelFormat;
 _pipeline=[self.device newRenderPipelineStateWithDescriptor:descriptor error:&error];
 _loading=[[UILabel alloc]initWithFrame:self.bounds];_loading.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;_loading.textAlignment=NSTextAlignmentCenter;_loading.textColor=UIColor.whiteColor;_loading.text=_pipeline?@"Loading original OpenTTD engine…":[NSString stringWithFormat:@"Metal initialization failed: %@",error];[self addSubview:_loading];
 UIPinchGestureRecognizer *pinch=[[UIPinchGestureRecognizer alloc]initWithTarget:self action:@selector(pinch:)];[self addGestureRecognizer:pinch];
 UIPanGestureRecognizer *pan=[[UIPanGestureRecognizer alloc]initWithTarget:self action:@selector(twoFingerPan:)];pan.minimumNumberOfTouches=2;pan.maximumNumberOfTouches=2;pan.delegate=self;[self addGestureRecognizer:pan];
 UITapGestureRecognizer *context=[[UITapGestureRecognizer alloc]initWithTarget:self action:@selector(contextTap:)];context.numberOfTouchesRequired=2;[self addGestureRecognizer:context];
 [context requireGestureRecognizerToFail:pan];
 return self;
}
-(BOOL)gestureRecognizer:(UIGestureRecognizer*)a shouldRecognizeSimultaneouslyWithGestureRecognizer:(UIGestureRecognizer*)b{return [a isKindOfClass:UIPinchGestureRecognizer.class]||[b isKindOfClass:UIPinchGestureRecognizer.class];}
-(void)layoutSubviews{
 [super layoutSubviews];CGSize size=self.bounds.size;if(size.width<320||size.height<240)return;
 if(!_started){
  _started=YES;_lastSize=size;
  NSFileManager *fm=NSFileManager.defaultManager;NSURL *documents=[fm URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
  NSURL *root=[documents URLByAppendingPathComponent:@"OpenTTD" isDirectory:YES];NSError *error=nil;
  NSURL *bundledData=[NSBundle.mainBundle.bundleURL URLByAppendingPathComponent:@"GameData" isDirectory:YES];
  if(![fm fileExistsAtPath:root.path]){
   NSURL *data=[NSBundle.mainBundle.bundleURL URLByAppendingPathComponent:@"GameData" isDirectory:YES];
   NSURL *stage=[documents URLByAppendingPathComponent:[@"OpenTTD-Install-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
   if(![fm copyItemAtURL:data toURL:stage error:&error]||![fm moveItemAtURL:stage toURL:root error:&error]){
    [fm removeItemAtURL:stage error:nil];_loading.text=[NSString stringWithFormat:@"Game data installation failed: %@",error];return;
   }
  }
  if(!InstallMissingResources(fm,bundledData,root,&error)){_loading.text=[NSString stringWithFormat:@"Game resource update failed: %@",error.localizedDescription];return;}
  if(!InstallClassicMenuIfUnmodified(bundledData,root,&error)){_loading.text=error.localizedDescription;return;}
  if(!RecoverNativeContentImports(root,&error)){_loading.text=error.localizedDescription;return;}
  ConfigureNativeContentImport(self.window.rootViewController,root);
  NSURL *config=[root URLByAppendingPathComponent:@"openttd.cfg"];
  if(![fm fileExistsAtPath:config.path]){
   NSString *settings=@"[misc]\nlanguage = english.lng\ngui_scale = 150\nsoundsset = OpenSFX\n\n[gui]\nautosave_on_exit = true\nrefresh_rate = 60\ntoolbar_dropdown_autoselect = false\n\n[game_creation]\nmap_x = 7\nmap_y = 7\nlandscape = temperate\n\n[graphicsset]\nname = OpenGFX\nshortname = 4F474658\n";
   if(![settings writeToURL:config atomically:YES encoding:NSUTF8StringEncoding error:&error]){_loading.text=error.localizedDescription;return;}
  }
  OTTDStart(root.path.UTF8String,(int)size.width,(int)size.height,Frame,Keyboard,(__bridge void*)self);
 }else if(!CGSizeEqualToSize(size,_lastSize)){_lastSize=size;OTTDResize(size.width,size.height);}
}
-(void)acceptPixels:(const void*)pixels width:(int)w height:(int)h metadata:(const char*)metadata{
 NSData *frame=[NSData dataWithBytes:pixels length:(NSUInteger)w*h*4];NSData *meta=[NSData dataWithBytes:metadata length:strlen(metadata)];
 [_frameLock lock];_latestPixels=frame;_latestMetadata=meta;_frameWidth=w;_frameHeight=h;[_frameLock unlock];
}
-(void)drawInMTKView:(MTKView*)view{
 [_frameLock lock];NSData *pixels=_latestPixels;NSData *metadata=_latestMetadata;int w=_frameWidth,h=_frameHeight;[_frameLock unlock];
 if(!pixels||!_pipeline)return;
 if(!_texture||_texture.width!=w||_texture.height!=h){MTLTextureDescriptor *d=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:w height:h mipmapped:NO];d.usage=MTLTextureUsageShaderRead;d.storageMode=MTLStorageModeShared;_texture=[self.device newTextureWithDescriptor:d];}
 [_texture replaceRegion:MTLRegionMake2D(0,0,w,h) mipmapLevel:0 withBytes:pixels.bytes bytesPerRow:w*4];
 id<CAMetalDrawable> drawable=self.currentDrawable;MTLRenderPassDescriptor *pass=self.currentRenderPassDescriptor;if(!drawable||!pass)return;
 id<MTLCommandBuffer> buffer=[_queue commandBuffer];id<MTLRenderCommandEncoder> encoder=[buffer renderCommandEncoderWithDescriptor:pass];[encoder setRenderPipelineState:_pipeline];[encoder setFragmentTexture:_texture atIndex:0];[encoder drawPrimitives:MTLPrimitiveTypeTriangleStrip vertexStart:0 vertexCount:4];[encoder endEncoding];[buffer presentDrawable:drawable];[buffer commit];[buffer waitUntilCompleted];
 _loading.hidden=YES;
 // Export real upstream widget bounds/labels, not duplicate native game controls.
 static NSData *previousMetadata=nil;BOOL relayout=!CGSizeEqualToSize(_accessibilitySize,self.bounds.size);if(![metadata isEqualToData:previousMetadata]||relayout){previousMetadata=metadata;_accessibilitySize=self.bounds.size;NSDictionary *data=[NSJSONSerialization JSONObjectWithData:metadata options:0 error:nil];
  if([data[@"tutorial_offer_ready"]boolValue])OfferNativeTouchTutorialIfNeeded();
  NSDictionary *dialog=[data[@"scrollable_dialogs"]firstObject];
  CGFloat top=[dialog[@"top"]doubleValue],bottom=[dialog[@"bottom"]doubleValue],height=[dialog[@"h"]doubleValue],visible=bottom-top;
  _dialogScrollIndicator.hidden=!dialog||height<=visible;
  if(!_dialogScrollIndicator.hidden){CGFloat thumb=MAX(24,visible*visible/height),position=MIN(1,MAX(0,(top-[dialog[@"y"]doubleValue])/(height-visible)));CGFloat x=MIN(w,[dialog[@"x"]doubleValue]+[dialog[@"w"]doubleValue])-4;
   _dialogScrollIndicator.frame=CGRectMake(x*self.bounds.size.width/w,(top+position*(visible-thumb))*self.bounds.size.height/h,3,thumb*self.bounds.size.height/h);
  }
  if(relayout||![data[@"widgets"] isEqual:_widgetDescriptions]){
  _widgetDescriptions=[data[@"widgets"] copy];NSMutableArray *elements=[NSMutableArray array];NSMutableDictionary *nextWidgets=[NSMutableDictionary dictionary];
  for(NSDictionary *widget in data[@"widgets"]){
   NSString *identifier=widget[@"id"];OTTDAccessibleWidget *element=_accessibleWidgets[identifier];
   if(!element)element=[[OTTDAccessibleWidget alloc]initWithAccessibilityContainer:self];
   element.accessibilityIdentifier=identifier;nextWidgets[identifier]=element;
   NSString *label=[[widget[@"label"] componentsSeparatedByCharactersInSet:[NSCharacterSet characterSetWithRange:NSMakeRange(0xE000,0x1900)]] componentsJoinedByString:@""];
   if(![element.accessibilityLabel isEqualToString:label])element.accessibilityLabel=label;
   element.accessibilityTraits=[widget[@"role"] isEqual:@"text"]?UIAccessibilityTraitStaticText:UIAccessibilityTraitButton|([widget[@"disabled"]boolValue]?UIAccessibilityTraitNotEnabled:0)|([widget[@"selected"]boolValue]?UIAccessibilityTraitSelected:0);
   element.accessibilityHint=[widget[@"highlighted"]boolValue]?@"Next tutorial action":dialog?@"Two-finger drag scrolls oversized windows. VoiceOver supports the scroll action.":nil;
   CGRect r=CGRectMake([widget[@"x"]doubleValue]*self.bounds.size.width/w,[widget[@"y"]doubleValue]*self.bounds.size.height/h,[widget[@"w"]doubleValue]*self.bounds.size.width/w,[widget[@"h"]doubleValue]*self.bounds.size.height/h);
   element.accessibilityFrameInContainerSpace=r;element.gamePoint=CGPointMake([widget[@"x"]floatValue]+[widget[@"w"]floatValue]/2,[widget[@"y"]floatValue]+[widget[@"h"]floatValue]/2);[elements addObject:element];
  }
  _accessibleWidgets=nextWidgets;
  if([data[@"map_centre_available"]boolValue]){
   if(!_worldElement)_worldElement=[[OTTDAccessibleWidget alloc]initWithAccessibilityContainer:self];_worldElement.accessibilityIdentifier=@"ottd.viewport";_worldElement.accessibilityLabel=@"Map centre";_worldElement.accessibilityTraits=UIAccessibilityTraitButton;_worldElement.gamePoint=CGPointMake(w/2,h/2);_worldElement.accessibilityFrameInContainerSpace=CGRectMake(self.bounds.size.width/2-22,self.bounds.size.height/2-22,44,44);[elements addObject:_worldElement];
  }
  // Preserve element identity as labels/pressed state change, retaining focus.
  if(![self.accessibilityElements isEqualToArray:elements])self.accessibilityElements=elements;
  }
  NSString *worldValue=[NSString stringWithFormat:@"%@ by %@ tiles. %@.",data[@"map_width"],data[@"map_height"],data[@"mode"]];
  if(![_worldElement.accessibilityValue isEqualToString:worldValue])_worldElement.accessibilityValue=worldValue;
 }
}
-(void)mtkView:(MTKView*)view drawableSizeWillChange:(CGSize)size{}
-(CGPoint)gamePoint:(CGPoint)p{[_frameLock lock];int w=_frameWidth,h=_frameHeight;[_frameLock unlock];return CGPointMake(p.x*(w?:self.bounds.size.width)/self.bounds.size.width,p.y*(h?:self.bounds.size.height)/self.bounds.size.height);}
-(void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{if(event.allTouches.count!=1){OTTDTouch(3,0,0);return;}CGPoint p=[self gamePoint:[touches.anyObject locationInView:self]];OTTDTouch(0,p.x,p.y);}
-(void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{if(event.allTouches.count!=1)return;CGPoint p=[self gamePoint:[touches.anyObject locationInView:self]];OTTDTouch(1,p.x,p.y);}
-(void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{CGPoint p=[self gamePoint:[touches.anyObject locationInView:self]];OTTDTouch(2,p.x,p.y);}
-(void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{OTTDTouch(3,0,0);}
-(void)pinch:(UIPinchGestureRecognizer*)g{
 if(g.state==UIGestureRecognizerStateBegan){OTTDTouch(3,0,0);_pinchRemainder=0;}
 CGPoint p=[self gamePoint:[g locationInView:self]];_pinchRemainder+=log(g.scale);g.scale=1;
 const CGFloat step=log(2.0);while(fabs(_pinchRemainder)>=step){int direction=_pinchRemainder>0?1:-1;OTTDZoom(direction,p.x,p.y);_pinchRemainder-=direction*step;}
}
-(void)twoFingerPan:(UIPanGestureRecognizer*)g{BOOL began=g.state==UIGestureRecognizerStateBegan;if(began){OTTDTouch(3,0,0);_twoFingerAnchor=[self gamePoint:[g locationInView:self]];}if(g.state==UIGestureRecognizerStateCancelled||g.state==UIGestureRecognizerStateFailed)return;CGPoint d=[g translationInView:self];CGPoint a=[self gamePoint:CGPointZero],b=[self gamePoint:d];OTTDGesturePan(b.x-a.x,b.y-a.y,_twoFingerAnchor.x,_twoFingerAnchor.y,began);[g setTranslation:CGPointZero inView:self];}
-(BOOL)scrollAccessible:(UIAccessibilityScrollDirection)direction atGamePoint:(CGPoint)point{
 CGFloat dx=0,dy=0;
 switch(direction){case UIAccessibilityScrollDirectionUp:case UIAccessibilityScrollDirectionNext:dy=-self.bounds.size.height*0.65;break;case UIAccessibilityScrollDirectionDown:case UIAccessibilityScrollDirectionPrevious:dy=self.bounds.size.height*0.65;break;case UIAccessibilityScrollDirectionLeft:dx=-self.bounds.size.width*0.65;break;case UIAccessibilityScrollDirectionRight:dx=self.bounds.size.width*0.65;break;default:return NO;}
 CGPoint delta=[self gamePoint:CGPointMake(dx,dy)];OTTDGesturePan(delta.x,delta.y,point.x,point.y,1);UIAccessibilityPostNotification(UIAccessibilityPageScrolledNotification,@"Scrolled");return YES;
}
-(BOOL)accessibilityScroll:(UIAccessibilityScrollDirection)direction{return [self scrollAccessible:direction atGamePoint:[self gamePoint:CGPointMake(self.bounds.size.width/2,self.bounds.size.height/2)]];}
-(void)contextTap:(UITapGestureRecognizer*)g{if(g.state==UIGestureRecognizerStateRecognized){CGPoint p=[self gamePoint:[g locationInView:self]];OTTDRightClick(p.x,p.y);}}
-(void)setKeyboardMode:(int)mode{
 if(mode==0){_keyboardMode=0;[_textInput resignFirstResponder];return;}
 // Original windows autofocus filters for hardware keyboards. Opening a file
 // or content list must not cover its rows with the software keyboard.
 if(mode==1&&_keyboardMode==2&&_textInput.isFirstResponder)return;
 _keyboardMode=mode;_textInput.replacementInputView=mode==2?nil:_hiddenKeyboard;
 if(_textInput.isFirstResponder)[_textInput reloadInputViews];else[_textInput becomeFirstResponder];
}
@end

@interface OTTDController:UIViewController@end
@implementation OTTDController
-(void)loadView{self.view=[UIView new];self.view.backgroundColor=UIColor.blackColor;static OTTDGameView *game=nil;if(!game)game=[[OTTDGameView alloc]initWithFrame:CGRectZero];else[game removeFromSuperview];game.translatesAutoresizingMaskIntoConstraints=NO;[self.view addSubview:game];[NSLayoutConstraint activateConstraints:@[[game.leadingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.leadingAnchor],[game.trailingAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.trailingAnchor],[game.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor],[game.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor]]];}
-(BOOL)prefersStatusBarHidden{return YES;}
-(void)viewDidAppear:(BOOL)animated{[super viewDidAppear:animated];NSURL *documents=[NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;ConfigureNativeContentImport(self,[documents URLByAppendingPathComponent:@"OpenTTD" isDirectory:YES]);ConfigureNativeTouchTutorial(self);}
-(BOOL)prefersHomeIndicatorAutoHidden{return YES;}
-(UIInterfaceOrientationMask)supportedInterfaceOrientations{return UIInterfaceOrientationMaskLandscape;}
-(UIInterfaceOrientation)preferredInterfaceOrientationForPresentation{return UIInterfaceOrientationLandscapeLeft;}
@end
@interface OTTDSceneDelegate:UIResponder<UIWindowSceneDelegate>
@property(nonatomic,strong)UIWindow *window;
@property(nonatomic)UIBackgroundTaskIdentifier backgroundTask;
-(void)finishBackgroundSave;
@end
static void BackgroundSaveFinished(void *context){
 OTTDSceneDelegate *owner=(__bridge_transfer OTTDSceneDelegate*)context;
 dispatch_async(dispatch_get_main_queue(),^{[owner finishBackgroundSave];});
}
@implementation OTTDSceneDelegate
-(void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options{self.backgroundTask=UIBackgroundTaskInvalid;self.window=[[UIWindow alloc]initWithWindowScene:(UIWindowScene*)scene];self.window.rootViewController=[OTTDController new];[self.window makeKeyAndVisible];}
-(void)finishBackgroundSave{if(self.backgroundTask!=UIBackgroundTaskInvalid){[UIApplication.sharedApplication endBackgroundTask:self.backgroundTask];self.backgroundTask=UIBackgroundTaskInvalid;}}
-(void)saveAndSuspend{
 if(self.backgroundTask!=UIBackgroundTaskInvalid)return;
 self.backgroundTask=[UIApplication.sharedApplication beginBackgroundTaskWithName:@"Save OpenTTD" expirationHandler:^{[self finishBackgroundSave];}];
 OTTDBackground(1,BackgroundSaveFinished,(__bridge_retained void*)self);
}
-(void)sceneDidEnterBackground:(UIScene*)scene{[self saveAndSuspend];}
-(void)sceneDidDisconnect:(UIScene*)scene{[self saveAndSuspend];}
-(void)sceneWillEnterForeground:(UIScene*)scene{OTTDBackground(0,nullptr,nullptr);}
@end
@interface OTTDAppDelegate:UIResponder<UIApplicationDelegate>@end
@implementation OTTDAppDelegate
-(BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)options{return YES;}
@end
int main(int argc,char *argv[]){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(OTTDAppDelegate.class));}}
