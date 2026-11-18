@rem 替换RK3568 ArkUI产物。
@echo off
set "SOURCE=%~1"

hdc wait-for-device shell cd etc
hdc target mount

for %%F in ("%SOURCE%\etc\abc\arkui\components\*.abc") do hdc file send "%%~fF" /system/etc/abc/arkui/components/
for %%F in ("%SOURCE%\etc\abc\arkui\*.abc") do hdc file send "%%~fF" /system/etc/abc/arkui/
for %%F in ("%SOURCE%\lib\libarkui_*.z.so") do hdc file send "%%~fF" /system/lib/

hdc file send "%SOURCE%\framework\arkoala.abc" /system/framework/
hdc file send "%SOURCE%\framework\promptAction.abc" /system/framework/
hdc file send "%SOURCE%\lib\libArkoalaNative_ark.z.so" /system/lib/
hdc file send "%SOURCE%\lib\libace_compatible_components.z.so" /system/lib/
hdc file send "%SOURCE%\lib\ndk\libace_ndk.z.so" /system/lib/ndk/
hdc file send "%SOURCE%\lib\platformsdk\libace_compatible.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libace_container_scope.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libace_engine_pa_ark.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libace_forward_compatibility.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libace_napi.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libace_uicontent.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\platformsdk\libui_session.z.so" /system/lib/platformsdk/
hdc file send "%SOURCE%\lib\module\liboverlay.z.so" /system/lib/module/
hdc file send "%SOURCE%\lib\liboverlayManager_ani.so" /system/lib/
hdc file send "%SOURCE%\lib\module\libprompt.z.so" /system/lib/module/
hdc file send "%SOURCE%\lib\module\ani\libprompt_ani.so" /system/lib/module/ani/
hdc file send "%SOURCE%\lib\module\libpromptaction.z.so" /system/lib/module/
hdc file send "%SOURCE%\lib\module\ani\libpromptAction_ani.so" /system/lib/module/ani/

hdc shell sync
hdc shell reboot
