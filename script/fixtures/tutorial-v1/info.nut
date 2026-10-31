/* GPL-2.0. A playable lesson using the original OpenTTD GameScript API. */
class TouchFirstRouteInfo extends GSInfo {
    function GetAuthor()      { return "OpenTTD Reimagined contributors"; }
    function GetName()        { return "Touch First Route"; }
    function GetDescription() { return "Learn the original controls by building and operating a real passenger bus route."; }
    function GetVersion()     { return 1; }
    function GetDate()        { return "2026-10-30"; }
    function CreateInstance(){ return "TouchFirstRoute"; }
    function GetShortName()   { return "TFR1"; }
    function GetAPIVersion()  { return "15"; }
    function MinVersionToLoad(){ return 1; }

}
RegisterGS(TouchFirstRouteInfo());
