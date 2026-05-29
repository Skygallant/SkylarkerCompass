if not A_IsAdmin
{
Run *RunAs "%A_ScriptFullPath%"
ExitApp
}
#SingleInstance Force


SetKeyDelay, 25

#IfWinActive, Star Citizen
^/::
Sleep, 100
Send, {F12}
Sleep, 200
Send, {Enter}
Sleep, 800
Send, /showlocation
Sleep, 100
Send, {Enter}
Sleep, 200
Send, {F12}
return

#If false
SetTimer, PeriodicF12Toggle, 600000

PeriodicF12Toggle:
if !WinExist("Star Citizen")
    return

wasStarCitizenActive := WinActive("Star Citizen")
rememberedWindow := ""

if (!wasStarCitizenActive)
{
    rememberedWindow := WinExist("A")
    WinActivate, Star Citizen
    WinWaitActive, Star Citizen,, 5
    if (ErrorLevel)
        return
}

Send, {F12}
Sleep, 200
Send, {F12}

if (!wasStarCitizenActive && rememberedWindow)
{
    if WinExist("ahk_id " rememberedWindow)
        WinActivate, ahk_id %rememberedWindow%
}
return
#If