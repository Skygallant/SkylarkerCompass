if not A_IsAdmin
{
Run *RunAs "%A_ScriptFullPath%"
ExitApp
}
#SingleInstance Force


SetKeyDelay, 25
#IfWinActive, Star Citizen                                              ;runs script only if Star Citien is running
LWin::                                                                  ;if right alt is pressed
prev:=WinActive("A")												  	;grab focus of currently selected window
WinActivate, Star Citizen												;in any case focus starcitizen
WinWait, Star Citizen													;waits until window is focussed
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