//
//  KathBot3
//
//  Created by  on 2009-08-19.
//  Copyright (c) 2009 AjaxLife Developments. All rights reserved.
//

default
{
    state_entry()
    {
        llSay(0, "Hello, Avatar!");
    }

    touch_start(integer total_number)
    {
        llSay(0, "Touched.");
    }
}
