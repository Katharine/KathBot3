string NOTIFY_SERVER = "http://inventory.sl:8765/secondlife"; // Change this to match your server.

key gRequestID;

MakeRequest(string page, list params) {
    string query = "";
    integer i;
    integer count;
    for(i = 0, count = llGetListLength(params); i < count; i += 2) {
        query += "&" + llEscapeURL(llList2String(params, i)) + "=" + llEscapeURL(llList2String(params, i+1));
    }
    query = "?" + llDeleteSubString(query, 0, 0);
    llHTTPRequest(NOTIFY_SERVER + "/" +  page + query, [], "");
}

HTTP_sensor() {
    llSensor("", NULL_KEY, AGENT, 96.0, PI);
}

HTTP_kick(key pest) {
    llUnSit(pest);
    llEjectFromLand(pest);
    llHTTPResponse(gRequestID, 200, "ok");
}

HTTP_ban(key pest) {
    llAddToLandBanList(pest, 0);
    llHTTPResponse(gRequestID, 200, "ok");
}

HTTP_pos() {
    llHTTPResponse(gRequestID, 200, llGetRegionName() + "\n" + (string)llGetPos());
}

HTTP_say(string message) {
    llSay(0, message);
    llHTTPResponse(gRequestID, 200, "ok");
}

HTTP_stats() {
    list response = [llGetRegionAgentCount(), llGetRegionFPS(), llGetRegionTimeDilation()];
    llHTTPResponse(gRequestID, 200, llDumpList2String(response, "|"));
}

default {
    state_entry() {
        llRequestURL();
    }
    
    http_request(key id, string method, string body) {
        if(method == URL_REQUEST_GRANTED) {
            llOwnerSay(body);
            MakeRequest("register", ["url", body, "description", llGetObjectDesc()]);
        } else if(method == URL_REQUEST_DENIED) {
            llOwnerSay("Couldn't get a URL! D:");
        } else if(method == "POST" || method == "GET") {
            string path = llGetHTTPHeader(id, "x-path-info");
            string request = llDeleteSubString(path, 0, 0);
            if(method == "GET") {
                body = llUnescapeURL(llGetHTTPHeader(id, "x-query-string"));
            }
            gRequestID = id;
            if(request == "sensor") {
                HTTP_sensor();
            } else if(request == "kick") {
                HTTP_kick(body);
            } else if(request == "ban") {
                HTTP_ban(body);
            } else if(request == "pos") {
                HTTP_pos();
            } else if(request == "say") {
                HTTP_say(body);
            } else if(request == "stats") {
                HTTP_stats();
            } else {
                llHTTPResponse(id, 404, "File Not Found");
            }
        }
    }
    
    sensor(integer num) {
        list response = [];
        integer i;
        for(i = 0; i < num; ++i) {
            list parts = [
                llDetectedKey(i),
                llDetectedName(i),
                llDetectedPos(i),
                llDetectedGroup(i),
                llDetectedVel(i),
                llDetectedRot(i),
                llGetAgentInfo(llDetectedKey(i))
            ];
            response += llDumpList2String(parts, "|");
        }
        llHTTPResponse(gRequestID, 200, llDumpList2String(response, "\n"));
    }
    
    no_sensor() {
        llHTTPResponse(gRequestID, 200, "");
    }
}