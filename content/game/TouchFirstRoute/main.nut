/* GPL-2.0. No vehicle purchases, orders or route operations are automated.
 * Setup validates the authored training landscape. Progress observes original
 * window events and actual world state through the unmodified GameScript API.
 */
class TouchFirstRoute extends GSController {
    state = null;
    function Tile(x, y) { return GSMap.GetTileIndex(x, y); }
    function Save() { return this.state == null ? {} : this.state; }
    function Load(version, data) { this.state = data; }
    function Require(ok, what) {
        if (!ok) throw "Training world preparation failed: " + what + " (" + GSError.GetLastErrorString() + ")";
    }
    function Prepare() {
        // The landscape is authored in the original scenario editor. Never
        // flatten an ordinary world or create the player's transport route.
        this.Require(GSMap.GetMapSizeX()==128 && GSMap.GetMapSizeY()==128, "load the First Route level");
        local towns=GSTownList();this.Require(towns.Count()==2, "the two lesson towns");
        local first=-1,second=-1;
        foreach(id,unused in towns){if(GSTown.GetLocation(id)==this.Tile(32,64))first=id;if(GSTown.GetLocation(id)==this.Tile(80,64))second=id;}
        this.Require(first!=-1&&second!=-1,"the authored town locations");
        for(local x=28;x<=84;x++)this.Require(GSRoad.IsRoadTile(this.Tile(x,64)),"the prepared public road");
        GSTown.SetName(first,"Meadow");GSTown.SetName(second,"Willow");
        foreach(marker in [[34,64,"1. Meadow bus stop"],[78,64,"2. Willow bus stop"],[48,65,"3. Bus depot (face road)"]])GSSign.BuildSign(this.Tile(marker[0],marker[1]),marker[2]);
        {local company=GSCompanyMode(0);GSCompany.SetName("Meadow Transport");}
        this.Require(GSGameSettings.SetValue("construction.command_pause_level",3),"enable the original paused-building setting for this lesson");
        this.state={step=0,page=-1,body=-1,button=-1,loaded_passengers=false};
        GSLog.Info("TOUCH_TUTORIAL_READY");
    }
    function Text() {
        local ids = [GSText.STR_STEP_0, GSText.STR_STEP_1, GSText.STR_STEP_2, GSText.STR_STEP_3, GSText.STR_STEP_4, GSText.STR_STEP_5, GSText.STR_STEP_6, GSText.STR_STEP_7, GSText.STR_STEP_8, GSText.STR_STEP_9, GSText.STR_STEP_10, GSText.STR_STEP_11, GSText.STR_STEP_12, GSText.STR_STEP_13, GSText.STR_STEP_14, GSText.STR_STEP_15, GSText.STR_STEP_16, GSText.STR_STEP_17];
        return GSText(ids[this.state.step]);
    }
    function ShowStep() {
        // Labels are placement aids. Remove only our exact markers once built,
        // so their viewport hit targets cannot cover a depot or order target.
        foreach(id,unused in GSSignList()) {
            local name=GSSign.GetName(id);
            if ((this.state.step>=4&&name=="1. Meadow bus stop") ||
                (this.state.step>=5&&name=="2. Willow bus stop") ||
                (this.state.step>=7&&name=="3. Bus depot (face road)")) GSSign.RemoveSign(id);
        }
        if (this.state.page == -1 || !GSStoryPage.IsValidStoryPage(this.state.page)) {
            this.state.page = GSStoryPage.New(0, "First route - learn by playing");
            this.state.body = GSStoryPage.NewElement(this.state.page, GSStoryPage.SPET_TEXT, 0, this.Text());
            local format = GSStoryPage.MakePushButtonReference(GSStoryPage.SPBC_GREEN, 0);
            this.state.button = GSStoryPage.NewElement(this.state.page, GSStoryPage.SPET_BUTTON_PUSH, format, "Begin lesson");
        } else this.Require(GSStoryPage.UpdateElement(this.state.body, 0, this.Text()), "update lesson text");
        if (this.state.step > 0 && GSStoryPage.IsValidStoryPageElement(this.state.button)) GSStoryPage.RemoveElement(this.state.button);
        GSStoryPage.Show(this.state.page);
        if(this.state.step==3||this.state.step==12) GSViewport.ScrollTo(this.Tile(34,64));
        else if(this.state.step==4||this.state.step==13) GSViewport.ScrollTo(this.Tile(78,64));
        else if(this.state.step>=5&&this.state.step<=11) GSViewport.ScrollTo(this.Tile(48,65));
        GSLog.Info("TOUCH_TUTORIAL_STEP " + this.state.step);
    }
    function Highlight(window, number, widget) {
        if (GSWindow.IsOpen(window, number)) GSWindow.Highlight(window, number, widget, GSWindow.TC_YELLOW);
    }
    function RoadTools() {
        if(GSWindow.IsOpen(GSWindow.WC_BUILD_TOOLBAR,1)) return true;
        if(GSWindow.IsOpen(GSWindow.WC_DROPDOWN_MENU,0)) this.Highlight(GSWindow.WC_DROPDOWN_MENU,0,GSWindow.WID_DM_ITEMS);
        else this.Highlight(GSWindow.WC_MAIN_TOOLBAR,0,GSWindow.WID_TN_ROADS);
        return false;
    }
    function StopTools() {
        if(!this.RoadTools()) return;
        if(GSWindow.IsOpen(GSWindow.WC_BUS_STATION,1)) this.Highlight(GSWindow.WC_BUS_STATION,1,GSWindow.WID_BROS_STATION_X);
        else this.Highlight(GSWindow.WC_BUILD_TOOLBAR,1,GSWindow.WID_ROT_BUS_STATION);
    }
    function DepotTools() {
        if(!this.RoadTools()) return;
        if(GSWindow.IsOpen(GSWindow.WC_BUILD_DEPOT,1)) this.Highlight(GSWindow.WC_BUILD_DEPOT,1,GSWindow.WID_BROD_DEPOT_NW);
        else this.Highlight(GSWindow.WC_BUILD_TOOLBAR,1,GSWindow.WID_ROT_DEPOT);
    }
    function ClearHighlights() {
        foreach (window in [GSWindow.WC_MAIN_TOOLBAR,GSWindow.WC_BUILD_TOOLBAR,GSWindow.WC_BUS_STATION,GSWindow.WC_BUILD_DEPOT,GSWindow.WC_VEHICLE_DEPOT,GSWindow.WC_BUILD_VEHICLE,GSWindow.WC_VEHICLE_VIEW,GSWindow.WC_VEHICLE_ORDERS]) {
            local number = (window == GSWindow.WC_BUILD_TOOLBAR || window == GSWindow.WC_BUS_STATION || window == GSWindow.WC_BUILD_DEPOT) ? 1 : 0;
            if (window == GSWindow.WC_VEHICLE_DEPOT || window == GSWindow.WC_BUILD_VEHICLE) number = this.Tile(48,65);
            if (window == GSWindow.WC_VEHICLE_VIEW || window == GSWindow.WC_VEHICLE_ORDERS) number = this.Bus();
            if (number != -1 && GSWindow.IsOpen(window, number)) GSWindow.Highlight(window,number,GSWindow.WIDGET_ALL,GSWindow.TC_INVALID);
        }
    }
    function Pace() { if(this.state.step<14) GSGame.Pause();else GSGame.Unpause(); }
    function Advance() { this.ClearHighlights(); this.state.step++; this.ShowStep();this.Pace(); }
    function ReturnTo(step) { this.ClearHighlights();this.state.step=step;this.ShowStep();this.Pace(); }
    function Bus() {
        local company = GSCompanyMode(0);
        foreach (id, unused in GSVehicleList()) if (GSVehicle.GetVehicleType(id)==GSVehicle.VT_ROAD && GSVehicle.GetCapacity(id,0)>0) return id;
        return -1;
    }
    function HasStop(x) {
        local tile=this.Tile(x,64);
        if (!GSRoad.IsDriveThroughRoadStationTile(tile)) return false;
        if (!GSStation.HasStationType(GSStation.GetStationID(tile),GSStation.STATION_BUS_STOP)) return false;
        local front=GSRoad.GetRoadStationFrontTile(tile);
        return (front==this.Tile(x-1,64)||front==this.Tile(x+1,64)) && GSStation.GetOwner(GSStation.GetStationID(tile))==0;
    }
    function HasOrder(bus, x) {
        if (bus == -1 || !this.HasStop(x)) return false;
        local company = GSCompanyMode(0);
        for (local i=0; i<GSOrder.GetOrderCount(bus); i++) if (GSStation.GetStationID(GSOrder.GetOrderDestination(bus,i))==GSStation.GetStationID(this.Tile(x,64))) return true;
        return false;
    }
    function Tick() {
        local bus = this.Bus(), depot = this.Tile(48,65), step = this.state.step;
        // Recover from ordinary beginner mistakes instead of completing a
        // stale checklist after a station, depot, vehicle or order is removed.
        if(step>3&&step<17&&!this.HasStop(34)){this.ReturnTo(3);return;}
        if(step>4&&step<17&&!this.HasStop(78)){this.ReturnTo(4);return;}
        if(step>6&&step<17&&(!GSRoad.IsRoadDepotTile(depot)||GSRoad.GetRoadDepotFrontTile(depot)!=this.Tile(48,64))){this.ReturnTo(6);return;}
        if(step>9&&step<17&&bus==-1){this.ReturnTo(7);return;}
        if(step>12&&step<17&&!this.HasOrder(bus,34)){this.ReturnTo(12);return;}
        if(step>13&&step<17&&!this.HasOrder(bus,78)){this.ReturnTo(13);return;}
        while (GSEventController.IsEventWaiting()) {
            local event = GSEventController.GetNextEvent();
            if (step==0 && event.GetEventType()==GSEvent.ET_STORYPAGE_BUTTON_CLICK) {
                local button = GSEventStoryPageButtonClick.Convert(event);
                if (button.GetElementID()==this.state.button) { this.Advance(); return; }
            }
        }
        if (step==1) { if(this.RoadTools()) this.Advance(); }
        else if (step==2) { if(this.RoadTools()) this.Highlight(GSWindow.WC_BUILD_TOOLBAR,1,GSWindow.WID_ROT_BUS_STATION); if(GSWindow.IsOpen(GSWindow.WC_BUS_STATION,1)) this.Advance(); }
        else if (step==3 || step==4) { this.StopTools(); if(this.HasStop(34)&&(step==3||this.HasStop(78))) this.Advance(); }
        else if (step==5) { this.DepotTools(); if(GSWindow.IsOpen(GSWindow.WC_BUILD_DEPOT,1)) this.Advance(); }
        else if (step==6) { this.DepotTools(); if(GSRoad.IsRoadDepotTile(depot)&&GSRoad.GetRoadDepotFrontTile(depot)==this.Tile(48,64)) this.Advance(); }
        else if (step==7 && GSWindow.IsOpen(GSWindow.WC_VEHICLE_DEPOT,depot)) this.Advance();
        else if (step==8) { this.Highlight(GSWindow.WC_VEHICLE_DEPOT,depot,GSWindow.WID_D_BUILD); if(GSWindow.IsOpen(GSWindow.WC_BUILD_VEHICLE,depot)) this.Advance(); }
        else if (step==9) { this.Highlight(GSWindow.WC_BUILD_VEHICLE,depot,GSWindow.WID_BV_BUILD); if(bus!=-1) this.Advance(); }
        else if (step==10 && bus!=-1 && GSWindow.IsOpen(GSWindow.WC_VEHICLE_VIEW,bus)) this.Advance();
        else if (step==11 && bus!=-1) { this.Highlight(GSWindow.WC_VEHICLE_VIEW,bus,GSWindow.WID_VV_SHOW_ORDERS); if(GSWindow.IsOpen(GSWindow.WC_VEHICLE_ORDERS,bus)) this.Advance(); }
        else if (step==12 && bus!=-1) { this.Highlight(GSWindow.WC_VEHICLE_ORDERS,bus,GSWindow.WID_O_GOTO); if(this.HasOrder(bus,34)) this.Advance(); }
        else if (step==13 && bus!=-1) { this.Highlight(GSWindow.WC_VEHICLE_ORDERS,bus,GSWindow.WID_O_GOTO); if(this.HasOrder(bus,34)&&this.HasOrder(bus,78)) this.Advance(); }
        else if (step==14 && bus!=-1) { this.Highlight(GSWindow.WC_VEHICLE_VIEW,bus,GSWindow.WID_VV_START_STOP); local moving=false;{local company=GSCompanyMode(0);moving=GSVehicle.GetCurrentSpeed(bus)>0;}if(moving)this.Advance(); }
        else if (step==15 && bus!=-1) { this.Highlight(GSWindow.WC_MAIN_TOOLBAR,0,GSWindow.WID_TN_FAST_FORWARD);local loaded=false;{local company=GSCompanyMode(0);loaded=GSVehicle.GetCargoLoad(bus,0)>0;}if(loaded)this.Advance(); }
        else if (step==16) { this.Highlight(GSWindow.WC_MAIN_TOOLBAR,0,GSWindow.WID_TN_FAST_FORWARD);if(GSCompany.GetQuarterlyIncome(0,GSCompany.CURRENT_QUARTER)>0)this.Advance(); }
    }
    function Start() {
        // GSWindow is local single-player UI. A hosted lesson must never leave
        // a multiplayer server paused waiting for a local button click.
        if (GSGame.IsMultiplayer()) {
            GSGame.Unpause();
            GSLog.Warning("First Route is a single-player lesson. Multiplayer coaching is disabled.");
            while (true) this.Sleep(100);
        }
        while (GSCompany.ResolveCompanyID(0) != 0) this.Sleep(1);
        // Script storage starts with INVALID_ROADTYPE, including after load.
        // Road/depot/station queries require an explicitly selected road type.
        GSRoad.SetCurrentRoadType(GSRoad.ROADTYPE_ROAD);
        if (this.state == null || !this.state.rawin("step")) this.Prepare();
        this.ShowStep(); GSViewport.ScrollTo(this.Tile(55,64));
        this.Pace();
        while (true) { this.Tick(); this.Sleep(5); }
    }
}
