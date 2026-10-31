// GPL-2.0: platform adapter for the original OpenTTD 15.3 engine.
#include "stdafx.h"
#include "EngineBridge.h"
#include "AudioDriver.h"
#include "base_media_sounds.h"
#include "base_media_graphics.h"
#include "base_media_music.h"
#include "fileio_func.h"
#include "fios.h"
#include "ai/ai.hpp"
#include "game/game.hpp"
#include "game/game_info.hpp"
#include "game/game_instance.hpp"
#include "story_base.h"
#include "openttd.h"
#include "core/random_func.hpp"
#include "video/video_driver.hpp"
#include "blitter/factory.hpp"
#include "palette_func.h"
#include "window_func.h"
#include "window_gui.h"
#include "gui.h"
#include "widgets/story_widget.h"
#include "viewport_func.h"
#include "tilehighlight_func.h"
#include "tilehighlight_type.h"
#include "gfx_func.h"
#include "map_func.h"
#include "tile_map.h"
#include "landscape.h"
#include "zoom_func.h"
#include "town.h"
#include "industry.h"
#include "progress.h"
#include "settings_func.h"
#include "settings_type.h"
#include "newgrf_config.h"
#include "strings_func.h"
#include "timer/timer_game_tick.h"
#include "saveload/saveload.h"
#include "3rdparty/nlohmann/json.hpp"
#include "../shared/TutorialGuide.h"
#include <fstream>
#include <unistd.h>
#include <csignal>
#include <deque>

extern void VisitDropDownListRows(const std::function<void(const Rect &, std::string_view, int, bool)> &visitor);
extern void VisitSaveLoadListRows(const std::function<void(const Rect &, std::string_view, int)> &visitor);
extern void VisitNetworkContentRows(const std::function<void(const Rect &, const Rect &, std::string_view, int, bool)> &visitor);
extern void VisitNewGRFRows(const std::function<void(const Rect &, std::string_view, int, bool)> &visitor);
extern void VisitNativeStoryButtons(const std::function<void(const Rect &, std::string_view, uint32_t)> &visitor);
extern void RefreshNativeSaveLoadFiles();
extern bool RefreshNativeNewGRFs();
extern void RefreshNativeMainMenuLayout();
uint _openttd_touch_target=44;

namespace {
struct Event {int kind;float x,y;int n=0;std::string text;OTTDCompletion completion=nullptr;void *context=nullptr;float anchor_x=0,anchor_y=0;};
std::mutex events_mutex;
std::deque<Event> events;
OTTDFrameCallback on_frame=nullptr;
OTTDKeyboardCallback on_keyboard=nullptr;
void *callback_context=nullptr;
std::once_flag start_once;
std::string session_root;
int initial_width=1194,initial_height=834;
void Push(Event e){std::lock_guard<std::mutex> guard(events_mutex);events.push_back(std::move(e));}
void Cursor(int x,int y){_cursor.in_window=true;_cursor.UpdateCursorPosition(Clamp(x,0,_screen.width-1),Clamp(y,0,_screen.height-1));}
void Mouse(bool down){_left_button_down=down;if(!down)_left_button_clicked=false;HandleMouseEvents();}
void Pan(float dx,float dy){
 Window *w=GetMainWindow();if(!w||!w->viewport)return;
 auto &v=*w->viewport;v.CancelFollow(*w);
 int x=static_cast<int>(dx*(1<<static_cast<int>(v.zoom))),y=static_cast<int>(dy*(1<<static_cast<int>(v.zoom)));
 v.scrollpos_x-=x;v.scrollpos_y-=y;v.dest_scrollpos_x=v.scrollpos_x;v.dest_scrollpos_y=v.scrollpos_y;
 w->SetDirty();
}
struct DialogArea {int top,bottom;};
DialogArea GetDialogArea(){
 auto *toolbar=FindWindowById(WC_MAIN_TOOLBAR,0),*status=FindWindowById(WC_STATUS_BAR,0);
 return {toolbar?toolbar->top+toolbar->height:0,status?status->top:_screen.height};
}
bool ScrollableDialog(Window *w){
 if(!w||w==GetMainWindow()||w->window_class==WC_MAIN_TOOLBAR||w->window_class==WC_STATUS_BAR||w->window_class==WC_DROPDOWN_MENU||w->window_class==WC_TOOLTIPS)return false;
 auto area=GetDialogArea();return w->height>area.bottom-area.top||w->width>_screen.width;
}
class IPadVideo final:public VideoDriver {
 std::vector<uint32_t> pixels;
 Palette palette{};
 bool candidate=false,building=false,pressed=false,panning=false,suspended=false,active_touch=false,edit_tap=false;
 float start_x=0,start_y=0,last_x=0,last_y=0;
 float pan_remainder_x=0,pan_remainder_y=0,wheel_remainder=0;
#ifdef OTTD_RUNTIME_EVIDENCE
 std::array<float,4> last_gesture_pan{};uint64_t gesture_pan_sequence=0;
#endif
 uint64_t frames=0;
 std::chrono::steady_clock::time_point last_status{};
 std::string metadata="{}";
 decltype(_game_mode) observed_mode=GM_BOOTSTRAP;
 uint64_t observed_tick=0;bool observed_progress=false;
 std::array<float,3> last_pointer{};uint64_t input_sequence=0;
 uint32_t pending_content=0;
 void GesturePan(const Event &e){
#ifdef OTTD_RUNTIME_EVIDENCE
  last_gesture_pan={e.x,e.y,e.anchor_x,e.anchor_y};++gesture_pan_sequence;
#endif
  if(e.n)pan_remainder_x=pan_remainder_y=wheel_remainder=0;
  auto *w=FindWindowFromPt(e.anchor_x,e.anchor_y);
  if(w==GetMainWindow()){Pan(e.x,e.y);return;}
  if(!ScrollableDialog(w)){
   if(w){wheel_remainder-=e.y;int steps=static_cast<int>(wheel_remainder/44);if(steps){wheel_remainder-=steps*44;Cursor(e.anchor_x,e.anchor_y);_cursor.wheel+=steps;HandleMouseEvents();}}
   return;
  }
  pan_remainder_x+=e.x;pan_remainder_y+=e.y;
  int dx=static_cast<int>(pan_remainder_x),dy=static_cast<int>(pan_remainder_y);
  pan_remainder_x-=dx;pan_remainder_y-=dy;
  auto area=GetDialogArea();
  int x=w->width>_screen.width?Clamp(w->left+dx,_screen.width-w->width,0):w->left;
  int y=w->height>area.bottom-area.top?Clamp(w->top+dy,area.bottom-w->height,area.top):w->top;
  if(x==w->left&&y==w->top)return;
  w->SetDirty();
  if(w->viewport){w->viewport->left+=x-w->left;w->viewport->top+=y-w->top;}
  w->left=x;w->top=y;w->SetDirty();
 }
 void BeginPress(){
  CloseWindowByClass(WC_TOOLTIPS);Mouse(true);pressed=true;
  if(edit_tap&&on_keyboard)on_keyboard(callback_context,2);
 }
 void EndPress(){
  if(HasModalProgress())_left_button_down=_left_button_clicked=false;
  else Mouse(false);
 }
 void RefreshContent(){
  if(!pending_content||HasModalProgress()||suspended)return;
  uint32_t kinds=std::exchange(pending_content,0);
  // Match the original content-download completion path. No NewGRF or script
  // interpretation runs on UIKit's thread or the document-provider worker.
  if(kinds&16){TarScanner::DoScan(TarScanner::Mode::Baseset);BaseGraphics::FindSets();BaseSounds::FindSets();BaseMusic::FindSets();SetWindowDirty(WC_GAME_OPTIONS,WN_GAME_OPTIONS_GAME_OPTIONS);}
  if(kinds&(32|64))AI::Rescan();
  if(kinds&(128|256))Game::Rescan();
  if(kinds&(2|4)){TarScanner::DoScan(TarScanner::Mode::Scenario);ScanScenarios();}
  if(kinds&8){if(!RefreshNativeNewGRFs())pending_content|=8;}
  if(kinds&(1|2|4))RefreshNativeSaveLoadFiles();
 }
 void Process(const Event &e){
  if(e.kind==11){pending_content|=static_cast<uint32_t>(e.n);return;}
  if(e.kind>=0&&e.kind<=3){last_pointer={float(e.kind),e.x,e.y};++input_sequence;}
  if(e.kind==4){ChangeResolution(e.x,e.y);return;}
  // Original generation workers own the world while modal progress is active.
  // Keep lifecycle delivery, but do not query or interact with that world.
  if(HasModalProgress()&&e.kind!=7&&e.kind!=10){
   // A release may arrive after the Generate button started a worker.
   _left_button_down=_left_button_clicked=false;
   _right_button_down=_right_button_clicked=false;
   candidate=building=panning=pressed=active_touch=false;
   return;
  }
  if(e.kind==13){
   auto *info=Game::GetInfo();
   if(_game_mode==GM_NORMAL&&info&&info->GetName()=="Touch First Route")ShowStoryBook(_local_company);
   else ShowFirstRouteGuide(e.text);
   return;
  }
  if(e.kind==5){Cursor(e.x,e.y);if(auto *w=GetMainWindow())ZoomInOrOutToCursorWindow(e.n>0,w);return;}
  if(e.kind==6){if(e.text.empty())HandleKeypress(e.n,0);else HandleTextInput(e.text);return;}
  if(e.kind==7){
   if(e.n)Process(Event{3,last_x,last_y});
   NativeAudioSetBackground(e.n!=0);
   if(e.n&&!suspended){
    if(!HasModalProgress()&&_game_mode==GM_NORMAL&&_settings_client.gui.autosave_on_exit){DoExitSave();WaitTillSaved();}
    SaveToConfig();
   }
   suspended=e.n;Describe();if(e.completion)e.completion(e.context);return;
  }
  if(e.kind==10){NativeAudioHandleInterruption(e.n);return;}
  if(e.kind==8){Pan(e.x,e.y);return;}
  if(e.kind==12){GesturePan(e);return;}
  if(e.kind==9){Cursor(e.x,e.y);_right_button_down=true;_right_button_clicked=true;HandleMouseEvents();_right_button_down=false;HandleMouseEvents();return;}
  Cursor(e.x,e.y);
  if(e.kind==0){
   NativeAudioUserActivity();
   // A finger has no preceding mouse-move event to dismiss a hover tooltip.
   CloseWindowByClass(WC_TOOLTIPS);
   start_x=last_x=e.x;start_y=last_y=e.y;panning=false;pressed=false;active_touch=true;
   auto *w=FindWindowFromPt(e.x,e.y);
   edit_tap=false;
   if(w){
    auto id=GetWidgetFromPos(w,int(e.x)-w->left,int(e.y)-w->top);
    auto it=w->widget_lookup.find(id);
    if(it!=w->widget_lookup.end()){
     auto *widget=dynamic_cast<NWidgetCore *>(it->second);
     edit_tap=widget&&widget->type==WWT_EDITBOX&&!widget->IsDisabled();
    }
   }
   candidate=w&&w==GetMainWindow();building=_thd.place_mode!=HT_NONE;
   // Original menus need a real press before release, with their event loop
   // running while the finger is down. Defer only world taps so navigation
   // does not accidentally invoke a construction tool.
   if(w&&!candidate)BeginPress();
  }else if(e.kind==1){
   if(!active_touch)return;
   if(candidate){
    if(!panning&&std::hypot(e.x-start_x,e.y-start_y)>7){
     panning=true;
     if(building){Cursor(start_x,start_y);BeginPress();Cursor(e.x,e.y);}
    }
    if(panning){if(building)HandleMouseEvents();else Pan(e.x-last_x,e.y-last_y);}
   }else{
    if(!pressed&&std::hypot(e.x-start_x,e.y-start_y)>7){Cursor(start_x,start_y);BeginPress();Cursor(e.x,e.y);}
    if(pressed&&!HasModalProgress())HandleMouseEvents();
   }
   last_x=e.x;last_y=e.y;
  }else if(e.kind==2){
   if(!active_touch){_cursor.in_window=false;return;}
   if((candidate&&!panning)||(!candidate&&!pressed)){Cursor(e.x,e.y);BeginPress();EndPress();}
   else if(pressed)EndPress();
   candidate=panning=pressed=active_touch=false;
   _cursor.in_window=false;
  }else if(e.kind==3){
   if(pressed&&candidate&&building&&panning)ResetObjectToPlace();
   if(pressed)EndPress();
   candidate=panning=pressed=active_touch=false;
  }
 }
 void Describe(){
  if(HasModalProgress()){
   metadata="{\"mode\":\"loading\",\"widgets\":[],\"map_centre_available\":false}";
   return;
  }
  nlohmann::json data;data["tick"]=TimerGameTick::counter;data["mode"]=_game_mode==GM_NORMAL?"normal":_game_mode==GM_MENU?"menu":_game_mode==GM_EDITOR?"editor":"bootstrap";data["frames"]=frames;data["gui_scale"]=_gui_scale;data["surface"]={_screen.width,_screen.height};
  data["map_width"]=Map::SizeX();data["map_height"]=Map::SizeY();data["widgets"]=nlohmann::json::array();data["scrollable_dialogs"]=nlohmann::json::array();
#ifdef OTTD_RUNTIME_EVIDENCE
  if(Map::SizeX()==128&&Map::SizeY()==128&&(_game_mode==GM_NORMAL||_game_mode==GM_EDITOR)){
   data["qa_tiles"]=nlohmann::json::array();
   if(auto *main=GetMainWindow();main&&main->viewport){
    const auto &v=*main->viewport;
    for(auto [x,y]:{std::pair{32,64},{80,64},{34,64},{78,64},{48,65},{28,64},{84,64},{35,64},{49,65}}){
     auto point=RemapCoords2(x*TILE_SIZE+TILE_SIZE/2,y*TILE_SIZE+TILE_SIZE/2);
     int sx=UnScaleByZoom(point.x-v.virtual_left,v.zoom)+v.left,sy=UnScaleByZoom(point.y-v.virtual_top,v.zoom)+v.top;
     data["qa_tiles"].push_back({{"tile",{x,y}},{"point",{sx,sy}},{"visible",sx>=0&&sy>=0&&sx<_screen.width&&sy<_screen.height&&FindWindowFromPt(sx,sy)==main}});
    }
   }
  }
#endif
  data["towns"]=Town::GetNumItems();data["industries"]=Industry::GetNumItems();
  auto audio=NativeAudioGetStatus();
  data["audio"]={{"available",audio.available},{"running",audio.running},{"background",audio.background},{"interrupted",audio.interrupted},{"callbacks",audio.callbacks},{"frames",audio.frames},{"non_silent_buffers",audio.non_silent_buffers},{"peak",audio.peak},{"last_error",audio.last_error},{"output_generation",audio.output_generation}};
  data["sound_set"]=BaseSounds::GetUsedSet()?BaseSounds::GetUsedSet()->name:"";
  data["graphics_set"]=BaseGraphics::GetUsedSet()?BaseGraphics::GetUsedSet()->name:"";
  data["landscape"]=int(_settings_game.game_creation.landscape);
  auto *menu=FindWindowById(WC_SELECT_GAME,0);
  data["tutorial_offer_ready"]=_game_mode==GM_MENU&&menu&&FindWindowFromPt(menu->left+menu->width/2,menu->top+menu->height/2)==menu;
#ifdef OTTD_RUNTIME_EVIDENCE
  NativeAudioWriteEvidence(session_root+"/native-first-sound.wav");
#endif
  data["newgrfs"]=nlohmann::json::array();
  if(auto *info=Game::GetInfo();info&&info->GetName()=="Touch First Route"){
   data["tutorial"]={{"active",true},{"log",nlohmann::json::array()},{"text",""}};
   if(auto *instance=Game::GetInstance()){
    const auto &log=instance->GetLogData();size_t start=log.size()>12?log.size()-12:0;
    for(size_t i=start;i<log.size();++i)data["tutorial"]["log"].push_back({{"type",int(log[i].type)},{"text",log[i].text}});
   }
   for(const auto *page:StoryPage::Iterate())if(page->title.GetDecodedString()=="First route - learn by playing")
    for(const auto *element:StoryPageElement::Iterate())if(element->page==page->index){
     if(element->type==SPET_TEXT)data["tutorial"]["text"]=element->text.GetDecodedString();
     if(element->type==SPET_LOCATION)data["tutorial"]["target"]={{"tile",element->referenced_id},{"label",element->text.GetDecodedString()}};
    }
  }
  for(const auto &grf:_grfconfig)data["newgrfs"].push_back({{"name",grf->GetName()},{"grfid",grf->ident.grfid},{"file",grf->filename},{"status",int(grf->status)}});
#ifdef OTTD_RUNTIME_EVIDENCE
  data["suspended"]=suspended;
  data["configured_render_hz"]=_settings_client.gui.refresh_rate;
  data["last_pointer"]=last_pointer;data["input_sequence"]=input_sequence;
  data["last_gesture_pan"]=last_gesture_pan;data["gesture_pan_sequence"]=gesture_pan_sequence;data["left_button_down"]=_left_button_down;data["active_touch"]=active_touch;
#ifdef OTTD_RUNTIME_EVIDENCE
  std::array<uint32_t,16> tile_counts{};for(TileIndex t{0};t<Map::Size();++t)++tile_counts[GetTileType(t)];data["tile_types"]=tile_counts;
#endif
#endif
  if(auto *main=GetMainWindow();main&&main->viewport){auto &v=*main->viewport;data["camera"]={v.scrollpos_x,v.scrollpos_y,static_cast<int>(v.zoom)};data["map_centre_available"]=_game_mode==GM_NORMAL&&FindWindowFromPt(_screen.width/2,_screen.height/2)==main;}
  for(auto *w:Window::IterateFromFront()){
   if(w->window_class==WC_STORY_BOOK&&data.contains("tutorial")&&!data["tutorial"]["text"].get<std::string>().empty()){
    auto *panel=w->GetWidget<NWidgetBase>(WID_SB_PAGE_PANEL);
    data["widgets"].push_back({{"id","ottd.tutorial.lesson.text"},{"role","text"},{"label",data["tutorial"]["text"]},{"x",w->left+int(panel->pos_x)},{"y",w->top+int(panel->pos_y)},{"w",panel->current_x},{"h",panel->current_y},{"disabled",false}});
   }
   if(ScrollableDialog(w)){auto area=GetDialogArea();data["scrollable_dialogs"].push_back({{"x",w->left},{"y",w->top},{"w",w->width},{"h",w->height},{"top",area.top},{"bottom",area.bottom}});}
#ifdef OTTD_RUNTIME_EVIDENCE
   data["windows"].push_back({{"class",int(w->window_class)},{"number",int32_t(w->window_number)},{"x",w->left},{"y",w->top},{"w",w->width},{"h",w->height}});
#endif
   if(auto *close=w->nested_root?w->nested_root->GetWidgetOfType(WWT_CLOSEBOX):nullptr;close&&close->current_x&&close->current_y){
    int x=w->left+close->pos_x,y=w->top+close->pos_y;
    if(FindWindowFromPt(x+close->current_x/2,y+close->current_y/2)==w)
     data["widgets"].push_back({{"id",fmt::format("ottd.close.{}.{}",int(w->window_class),int32_t(w->window_number))},{"label","Close window"},{"x",x},{"y",y},{"w",close->current_x},{"h",close->current_y},{"disabled",false}});
   }
   for(auto &[id,base]:w->widget_lookup){
    auto *c=dynamic_cast<NWidgetCore *>(base);if(!c||base->current_x<8||base->current_y<8)continue;
    int x=w->left+base->pos_x,y=w->top+base->pos_y,cx=x+base->current_x/2,cy=y+base->current_y/2;
    if(cx<0||cy<0||cx>=_screen.width||cy>=_screen.height||FindWindowFromPt(cx,cy)!=w||GetWidgetFromPos(w,cx-w->left,cy-w->top)!=id)continue;
    std::string label;
    if(c->GetString()!=0)label=w->GetWidgetString(id,c->GetString());
    if(label.empty()&&c->GetToolTip()!=0)label=w->GetWidgetString(id,c->GetToolTip());
    if(label.empty())continue;
    data["widgets"].push_back({{"id",fmt::format("ottd.{}.{}.{}",static_cast<int>(w->window_class),static_cast<int32_t>(w->window_number),id)}, {"label",label},{"x",x},{"y",y},{"w",base->current_x},{"h",base->current_y},{"disabled",c->IsDisabled()},{"selected",c->IsLowered()},{"highlighted",c->IsHighlighted()}});
   }
  }
  VisitDropDownListRows([&](const Rect &r,std::string_view text,int result,bool disabled){
   data["widgets"].push_back({{"id",fmt::format("ottd.dropdown.{}",result)},{"label",text},{"x",r.left},{"y",r.top},{"w",r.Width()},{"h",r.Height()},{"disabled",disabled}});
  });
  VisitFirstRouteGuideText([&](const Rect &r,const std::string &text){data["widgets"].push_back({{"id","ottd.tutorial.guide.text"},{"role","text"},{"label",text},{"x",r.left},{"y",r.top},{"w",r.Width()},{"h",r.Height()},{"disabled",false}});});
  VisitNativeStoryButtons([&](const Rect &r,std::string_view text,uint32_t id){data["widgets"].push_back({{"id",fmt::format("ottd.story.{}",id)},{"label",text},{"x",r.left},{"y",r.top},{"w",r.Width()},{"h",r.Height()},{"disabled",false}});});
  VisitSaveLoadListRows([&](const Rect &r,std::string_view text,int index){
   data["widgets"].push_back({{"id",fmt::format("ottd.file.{}",index)},{"label",text},{"x",r.left},{"y",r.top},{"w",r.Width()},{"h",r.Height()},{"disabled",false}});
  });
  VisitNetworkContentRows([&](const Rect &r,const Rect &box,std::string_view text,int index,bool disabled){
   data["widgets"].push_back({{"id",fmt::format("ottd.content.row.{}",index)},{"label",text},{"x",r.left+(box.right-r.left+1)},{"y",r.top},{"w",r.right-box.right},{"h",r.Height()},{"disabled",false}});
   data["widgets"].push_back({{"id",fmt::format("ottd.content.select.{}",index)},{"label",fmt::format("Select download: {}",text)},{"x",box.left},{"y",box.top},{"w",box.Width()},{"h",box.Height()},{"disabled",disabled}});
  });
  VisitNewGRFRows([&](const Rect &r,std::string_view text,int index,bool active){
   data["widgets"].push_back({{"id",fmt::format("ottd.newgrf.{}.{}",active?"active":"available",index)},{"label",text},{"x",r.left},{"y",r.top},{"w",r.Width()},{"h",r.Height()},{"disabled",false}});
  });
  metadata=data.dump();
#ifdef OTTD_RUNTIME_EVIDENCE
  auto tmp=session_root+"/native-session.json.tmp";
  std::ofstream(tmp)<<metadata;std::rename(tmp.c_str(),(session_root+"/native-session.json").c_str());
#endif
 }
public:
 IPadVideo(){is_game_threaded=false;}
 std::string_view GetName()const override{return "ipad";}
 std::optional<std::string_view> Start(const StringList &)override{
  _resolutions={{1024,768},{1194,834},{1366,1024}};
  ChangeResolution(initial_width,initial_height);_cursor.in_window=true;return std::nullopt;
 }
 void Stop()override{}
 void MakeDirty(int,int,int,int)override{}
 bool ChangeResolution(int w,int h)override{
  w=Clamp(w,640,4096);h=Clamp(h,400,3072);
  pixels.assign(static_cast<size_t>(w)*h,0xff000000);
  _screen.width=_screen.pitch=w;_screen.height=h;_screen.dst_ptr=pixels.data();_cur_resolution={static_cast<uint>(w),static_cast<uint>(h)};
  BlitterFactory::GetCurrentBlitter()->PostResize();
  GameSizeChanged();RefreshNativeMainMenuLayout();return true;
 }
 bool ToggleFullscreen(bool)override{return true;}
 bool AfterBlitterChange()override{return ChangeResolution(_screen.width,_screen.height);}
 void EditBoxGainedFocus()override{if(on_keyboard)on_keyboard(callback_context,1);}
 void EditBoxLostFocus()override{if(on_keyboard)on_keyboard(callback_context,0);}
 void MainLoop()override{
  next_game_tick=next_draw_tick=std::chrono::steady_clock::now();
  while(!_exit_game){
   // Suspension must still drain the owned event queue so foregrounding can resume.
   if(suspended){std::deque<Event> work;{std::lock_guard<std::mutex> guard(events_mutex);work.swap(events);}for(auto &e:work)Process(e);std::this_thread::sleep_for(std::chrono::milliseconds(20));next_game_tick=next_draw_tick=std::chrono::steady_clock::now();continue;}
   RefreshContent();RefreshFirstRouteTarget();Tick();SleepTillNextTick();
  }
 }
 bool PollEvent()override{
  Event e;{std::lock_guard<std::mutex> guard(events_mutex);if(events.empty())return false;e=std::move(events.front());events.pop_front();}Process(e);return true;
 }
 void CheckPaletteAnim()override{
  if(CopyPalette(palette,false)&&palette.count_dirty){BlitterFactory::GetCurrentBlitter()->PaletteAnimate(palette);palette.count_dirty=0;}
 }
 void Paint()override{
  bool progress=HasModalProgress();
  if(!progress){
   if(observed_mode!=_game_mode||observed_progress||TimerGameTick::counter<observed_tick)MarkWholeScreenDirty();
   observed_mode=_game_mode;observed_tick=TimerGameTick::counter;
  }
  observed_progress=progress;
  ++frames;auto now=std::chrono::steady_clock::now();
  if(now-last_status>std::chrono::milliseconds(250)){Describe();last_status=now;}
  if(on_frame)on_frame(callback_context,pixels.data(),_screen.width,_screen.height,metadata.c_str());
 }
};
class IPadFactory final:public DriverFactoryBase {
public:IPadFactory():DriverFactoryBase(Driver::DT_VIDEO,10,"ipad","Native iPad CPU renderer / Metal presentation"){}
 std::unique_ptr<Driver>CreateInstance()const override{return std::make_unique<IPadVideo>();}
} ipad_factory;
}
extern "C" void OTTDStart(const char *root,int w,int h,OTTDFrameCallback frame,OTTDKeyboardCallback keyboard,void *context){
 std::call_once(start_once,[=]{session_root=root;initial_width=w;initial_height=h;on_frame=frame;on_keyboard=keyboard;callback_context=context;
  std::thread([]{
   chdir(session_root.c_str());std::signal(SIGPIPE,SIG_IGN);
   std::string config=session_root+"/openttd.cfg";
   std::vector<std::string> values={"OpenTTDPad","-X","-c",config,"-M","NoMusic","-mnull","-v","ipad","-b","32bpp-anim","-d","misc=1,driver=1"};
   std::vector<std::string_view> args;for(auto &v:values)args.push_back(v);
   SetRandomSeed(static_cast<uint32_t>(time(nullptr)));
   int result=openttd_main(args);fprintf(stderr,"OpenTTD engine returned %d\n",result);
   std::exit(result);
  }).detach();
 });
}
extern "C" void OTTDTouch(int phase,float x,float y){Push({phase,x,y});}
extern "C" void OTTDZoom(int direction,float x,float y){Push({5,x,y,direction});}
extern "C" void OTTDPan(float dx,float dy){Push({8,dx,dy});}
extern "C" void OTTDGesturePan(float dx,float dy,float x,float y,int began){Event e{12,dx,dy,began};e.anchor_x=x;e.anchor_y=y;Push(std::move(e));}
extern "C" void OTTDResize(int w,int h){Push({4,static_cast<float>(w),static_cast<float>(h)});}
extern "C" void OTTDKey(unsigned key,const char *text){Push({6,0,0,static_cast<int>(key),text?text:""});}
extern "C" void OTTDBackground(int suspended,OTTDCompletion completion,void *context){Event event{7,0,0,suspended};event.completion=completion;event.context=context;Push(std::move(event));}
extern "C" void OTTDRightClick(float x,float y){Push({9,x,y});}
extern "C" void OTTDNotifyAudioEvent(int event){Push({10,0,0,event});}
extern "C" void OTTDContentChanged(uint32_t kinds){Push({11,0,0,static_cast<int>(kinds)});}
extern "C" void OTTDShowTutorial(const char *path){Push({13,0,0,0,path?path:""});}
