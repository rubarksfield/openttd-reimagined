#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef void (*OTTDFrameCallback)(void *,const void *,int,int,const char *);
typedef void (*OTTDKeyboardCallback)(void *,int);
typedef void (*OTTDCompletion)(void *);
void OTTDStart(const char *root,int width,int height,OTTDFrameCallback frame,OTTDKeyboardCallback keyboard,void *context);
void OTTDTouch(int phase,float x,float y); /* 0 down, 1 move, 2 up, 3 cancel */
void OTTDZoom(int direction,float x,float y);
void OTTDPan(float dx,float dy);
/* Pan the map, or scroll an oversized original dialog under the gesture anchor. */
void OTTDGesturePan(float dx,float dy,float anchor_x,float anchor_y,int began);
void OTTDResize(int width,int height);
void OTTDKey(unsigned key,const char *text);
void OTTDBackground(int suspended,OTTDCompletion completion,void *context);
void OTTDRightClick(float x,float y);
void OTTDNotifyAudioEvent(int event); /* 1 began, 0 resume allowed, 2 reset, 3 ended without auto-resume */
void OTTDContentChanged(uint32_t kinds);
void OTTDShowTutorial(const char *guide_path);
#ifdef __cplusplus
}
#endif
