import kivy
kivy.require('2.3.1')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform

# Hardware integration for Android
try:
    from plyer import accelerometer, call
except ImportError:
    print("Plyer not available — running in desktop mode.")
    accelerometer = None
    call = None


class SettingsDrawer(ModalView):
    """Handles the dark-themed side navigation drawer"""
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.populate_saved_number()

    def populate_saved_number(self):
        # Load existing number into the UI if it exists in JSON storage
        if self.app.store.exists('emergency_contact'):
            num = self.app.store.get('emergency_contact')['number']
            self.ids.saved_contacts_label.text = f"{num}"

    def save_contact(self):
        number = self.ids.phone_input.text.strip()
        if number and len(number) >= 5:
            self.app.store.put('emergency_contact', number=number)
            self.ids.saved_contacts_label.text = f"{number}"
            self.ids.phone_input.text = ""
        else:
            self.ids.phone_input.text = "Invalid number"

    def update_sensitivity(self, value):
        self.app.shock_threshold = value


class MainScreen(BoxLayout):
    """Handles the main visual states of the application"""
    
    # Dynamic variables bound directly to the KV UI colors and text
    status_text = StringProperty("MONITORING ACTIVE")
    status_color = ObjectProperty([0.2, 0.8, 0.2, 1]) # Bright Green
    
    gps_text = StringProperty("GPS: NETWORK (30.269)") 
    
    button_text = StringProperty("STOP MONITORING")
    button_color = ObjectProperty([0.4, 0.05, 0.05, 1]) # Dark Red
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.settings_drawer = SettingsDrawer(self.app)
        self.is_monitoring = False
        self.is_sos_active = False
        self.countdown_event = None
        self.seconds_left = 2

    def open_settings(self):
        self.settings_drawer.open()

    def toggle_state(self):
        """Handles the massive block button at the bottom of the screen."""
        if self.button_text == "CANCEL SOS":
            self.cancel_sos()
        elif self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """State: Active Monitoring"""
        self.is_monitoring = True
        self.status_text = "MONITORING ACTIVE"
        self.status_color = [0.2, 0.8, 0.2, 1] 
        self.button_text = "STOP MONITORING"
        self.button_color = [0.4, 0.05, 0.05, 1] 
        
        if accelerometer:
            try:
                accelerometer.enable()
            except Exception as e:
                print(f"Accelerometer error: {e}")

    def stop_monitoring(self):
        """State: Monitoring Paused"""
        self.is_monitoring = False
        self.status_text = "MONITORING STOPPED"
        self.status_color = [0.5, 0.5, 0.5, 1] 
        self.button_text = "START MONITORING"
        self.button_color = [0.1, 0.4, 0.1, 1] 
        
        if accelerometer:
            try:
                accelerometer.disable()
            except Exception:
                pass

    def trigger_shock_detected(self):
        """State: Emergency SOS Countdown"""
        self.is_sos_active = True
        self.seconds_left = 2
        
        self.status_text = f"IMPACT! SOS IN {self.seconds_left}s"
        self.status_color = [1, 0, 0, 1] 
        self.button_text = "CANCEL SOS"
        self.button_color = [0.6, 0, 0, 1] 
        
        # Start the 2-second countdown loop
        self.countdown_event = Clock.schedule_interval(self.update_countdown, 1)

    def update_countdown(self, dt):
        self.seconds_left -= 1
        if self.seconds_left > 0:
            self.status_text = f"IMPACT! SOS IN {self.seconds_left}s"
        else:
            self.countdown_event.cancel()
            self.app.make_emergency_call()
            self.cancel_sos() # Reset UI after executing call

    def cancel_sos(self):
        """Cancels the countdown and resets to the active monitoring state."""
        if self.countdown_event:
            self.countdown_event.cancel()
        self.is_sos_active = False
        self.start_monitoring()


class ShockDetectorApp(App):
    def build(self):
        self.store = JsonStore('shockdetector_storage.json')
        self.shock_threshold = 30.0 # Default sensitivity for impact force
        
        if platform == 'android':
            self.request_android_permissions()
            
        self.main_screen = MainScreen(self)
        return self.main_screen

    def on_start(self):
        self.main_screen.start_monitoring()
        Clock.schedule_interval(self.check_acceleration, 1.0 / 30.0)

    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            permissions = [Permission.CALL_PHONE, Permission.BODY_SENSORS]
            request_permissions(permissions)
        except Exception as e:
            print(f"Permission request failed: {e}")

    def check_acceleration(self, dt):
        if not self.main_screen.is_monitoring or self.main_screen.is_sos_active or not accelerometer:
            return
            
        val = accelerometer.acceleration
        if not val or all(v is None for v in val):
            return
            
        try:
            magnitude = (val[0] ** 2 + val[1] ** 2 + val[2] ** 2) ** 0.5
            if magnitude > self.shock_threshold:
                print(f"Shock detected! Magnitude: {magnitude:.2f}")
                self.main_screen.trigger_shock_detected()
        except TypeError:
            pass

    def make_emergency_call(self):
        if not self.store.exists('emergency_contact'):
            self.main_screen.gps_text = "NO CONTACT SAVED!"
            return
            
        number = self.store.get('emergency_contact')['number']
        print(f"Attempting to call {number}")
        
        if call:
            try:
                call.makecall(tel=number)
            except Exception as e:
                print(f"Call failed: {e}")
        else:
            print("Call not supported on this platform.")

    def on_pause(self):
        self.main_screen.stop_monitoring()
        return True

    def on_resume(self):
        self.main_screen.start_monitoring()


if __name__ == '__main__':
    ShockDetectorApp().run()
