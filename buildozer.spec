[app]
title = Shock Detector
package.name = shockdetector
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.3.1,plyer
orientation = portrait
fullscreen = 0
android.permissions = CALL_PHONE,BODY_SENSORS,VIBRATE,WAKE_LOCK
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.allow_backup = True
icon.filename = icon.png
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
