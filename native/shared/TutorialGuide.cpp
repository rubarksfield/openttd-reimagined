// GPL-2.0. The tutorial uses the original OpenTTD presentation.
#include "stdafx.h"
#include "TutorialGuide.h"
#include "window_gui.h"
#include "window_func.h"
#include "gfx_func.h"
#include "strings_func.h"
#include "openttd.h"
#include "fileio_func.h"
#include "saveload/saveload.h"
#include "gui.h"
#include "company_base.h"
#include "error.h"
#include "game/game.hpp"
#include "game/game_info.hpp"
#include "story_base.h"
#include "viewport_func.h"
#include "table/strings.h"
#include "3rdparty/nlohmann/json.hpp"
#include <fstream>
namespace {
enum : WidgetID { CAPTION, BODY, BACK, NEXT, PLAY };
static constexpr std::initializer_list<NWidgetPart> widgets = {
 NWidget(NWID_HORIZONTAL),
  NWidget(WWT_CLOSEBOX, COLOUR_DARK_GREEN),
  NWidget(WWT_CAPTION, COLOUR_DARK_GREEN, CAPTION), SetStringTip(STR_JUST_RAW_STRING),
 EndContainer(),
 NWidget(WWT_PANEL, COLOUR_DARK_GREEN, BODY), SetMinimalSize(350,130), SetFill(1,1), EndContainer(),
 NWidget(NWID_HORIZONTAL),
  NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, BACK), SetStringTip(STR_JUST_RAW_STRING), SetMinimalSize(110,0), SetFill(1,0),
  NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, NEXT), SetStringTip(STR_JUST_RAW_STRING), SetMinimalSize(110,0), SetFill(1,0),
 EndContainer(),
 NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, PLAY), SetStringTip(STR_JUST_RAW_STRING), SetMinimalSize(220,0), SetFill(1,0),
};
static WindowDesc description(WDP_CENTER,{},0,0,WC_HELPWIN,WC_NONE,{},widgets);
struct FirstRouteGuide final : Window {
 nlohmann::json pages;
 size_t page=0;
 FirstRouteGuide(WindowDesc &desc,WindowNumber number,nlohmann::json pages):Window(desc),pages(std::move(pages)){this->InitNested(number);Refresh();}
 void UpdateWidgetSize(WidgetID id,Dimension &size,const Dimension &,Dimension &,Dimension &)override{if(id==BACK||id==NEXT||id==PLAY)size.height=std::max<uint>(size.height,44);}
 void Refresh(){SetWidgetDisabledState(BACK,page==0);SetWidgetDisabledState(NEXT,page+1==pages.size());SetWidgetDisabledState(PLAY,_game_mode!=GM_MENU);SetDirty();}
 std::string GetWidgetString(WidgetID id,StringID fallback)const override{
  if(id==CAPTION)return "First steps - "+std::to_string(page+1)+" / "+std::to_string(pages.size());
  if(id==BACK)return "Previous";
  if(id==NEXT)return "Next";
  if(id==PLAY)return _game_mode==GM_MENU?"Play first-route lesson":"Start a lesson from the main menu";
  return Window::GetWidgetString(id,fallback);
 }
 void DrawWidget(const Rect &r,WidgetID id)const override{
  if(id!=BODY)return;
  const auto &p=pages[page];std::string text=p.value("title","")+"\n\n"+p.value("body","");
  DrawStringMultiLine(r.Shrink(12),text,TC_WHITE,SA_TOP|SA_LEFT);
 }
 void OnClick(Point,WidgetID id,int)override{
  if(id==BACK&&page>0){--page;Refresh();}
  if(id==NEXT&&page+1<pages.size()){++page;Refresh();}
  if(id==PLAY&&_game_mode==GM_MENU){
   const std::string file="scenario/First Route.sav";
   if(!FioCheckFileExists(file,NO_DIRECTORY)){
    ShowErrorMessage(GetEncodedString(STR_JUST_RAW_STRING,std::string("The First Route level is missing. Reinstall the app to restore the bundled lesson.")),{},WL_ERROR);return;
   }
   _file_to_saveload.name=file;_file_to_saveload.SetMode(FIOS_TYPE_FILE,SLO_LOAD);_switch_mode=SM_LOAD_GAME;this->Close();
  }
 }
};
}
void ShowFirstRouteGuide(const std::string &path){
 std::ifstream stream(path);auto guide=nlohmann::json::parse(stream,nullptr,false);
 if(guide.is_discarded()||!guide.contains("pages")||!guide["pages"].is_array()||guide["pages"].empty())return;
 AllocateWindowDescFront<FirstRouteGuide>(description,1001,guide["pages"]);
}
void VisitFirstRouteGuideText(const std::function<void(const Rect &,const std::string &)> &visitor){
 auto *base=FindWindowById(WC_HELPWIN,1001);if(!base)return;
 auto *w=static_cast<FirstRouteGuide *>(base);auto *body=w->GetWidget<NWidgetBase>(BODY);
 const auto &p=w->pages[w->page];std::string text=p.value("title","")+"\n\n"+p.value("body","");
 int x=w->left+int(body->pos_x),y=w->top+int(body->pos_y);
 visitor({x,y,x+int(body->current_x)-1,y+int(body->current_y)-1},text);
}

namespace {
TileIndex first_route_target = INVALID_TILE;
std::string first_route_target_label;
}
TileIndex FirstRouteTargetTile(){return first_route_target;}
void FocusFirstRouteTarget(TileIndex tile){
 if(tile!=first_route_target||tile==INVALID_TILE)return;
 if(auto *window=GetMainWindow();window&&window->viewport){
  while(window->viewport->zoom>ZoomLevel::In2x&&DoZoomInOutWindow(ZOOM_IN,window)){}
  ScrollMainWindowToTile(tile);
 }
}
std::string_view FirstRouteTargetLabel(){return first_route_target_label;}
void RefreshFirstRouteTarget(){
 TileIndex target=INVALID_TILE;std::string label;
 if(_game_mode==GM_NORMAL)if(auto *info=Game::GetInfo();info&&info->GetName()=="Touch First Route"){
  for(const auto *page:StoryPage::Iterate())if(page->title.GetDecodedString()=="First route - learn by playing"){
   for(const auto *element:StoryPageElement::Iterate())if(element->page==page->index&&element->type==SPET_LOCATION){
    auto text=element->text.GetDecodedString();
    if(text=="Show build tile"||text=="Show depot tile"||text=="Show destination tile"){
     target=TileIndex(element->referenced_id);
     label=text=="Show build tile"?"BUILD HERE":text=="Show depot tile"?"OPEN THIS DEPOT":"CHOOSE THIS STOP";
    }
   }
  }
 }
 if(target!=first_route_target||label!=first_route_target_label){
  first_route_target=target;first_route_target_label=label;FocusFirstRouteTarget(target);MarkWholeScreenDirty();
 }
}
