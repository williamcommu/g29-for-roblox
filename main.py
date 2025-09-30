#!/usr/bin/env python3
"""
Enhanced G29 Wheel to Roblox Interface
Multiple control modes for optimal compatibility and smoothness.
"""

import pygame
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard, mouse
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Button, Listener as MouseListener
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import win32gui
import win32con
from enum import Enum
import math

# Try to import vgamepad for virtual controller support
try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except ImportError:
    VGAMEPAD_AVAILABLE = False
    print("vgamepad not available - virtual controller mode disabled")


class ControlMode(Enum):
    """Different control modes for wheel input"""
    KEYBOARD = "keyboard"           # A/D keys (original mode)
    MOUSE_STEERING = "mouse"        # Mouse movement for steering
    VIRTUAL_XBOX = "virtual_xbox"   # Virtual Xbox controller
    HYBRID = "hybrid"               # Mouse steering + keyboard pedals


@dataclass
class WheelConfig:
    """Enhanced configuration for wheel input mapping"""
    # Control mode
    control_mode: str = ControlMode.MOUSE_STEERING.value
    
    # Steering settings
    steering_sensitivity: float = 1.0
    steering_deadzone: float = 0.05
    steering_range_degrees: float = 450.0  # Wheel rotation range (180-900 degrees)
    mouse_sensitivity: float = 3.0  # For mouse steering mode
    
    # Keyboard mode settings
    throttle_key: str = 'w'
    brake_key: str = 's'
    reverse_key: str = 's'
    handbrake_key: str = 'space'
    horn_key: str = 'h'
    
    # Keyboard steering LFO settings
    keyboard_steering_lfo: bool = True  # Use LFO-style rapid tapping
    keyboard_steering_frequency: float = 10.0  # Hz - how fast to tap keys
    
    # Pedal settings
    swap_brake_clutch: bool = False  # Use clutch pedal as brake (more accurate)
    
    # Mouse mode settings
    invert_mouse_steering: bool = False
    mouse_return_center: bool = True
    mouse_return_speed: float = 0.95
    
    # Virtual controller settings
    controller_steering_range: float = 1.0  # Full range -1 to 1
    controller_stick_mode: str = "left"  # "left", "right"
    controller_throttle_axis: str = "left_y"  # "left_x", "left_y", "right_x", "right_y", "triggers"
    
    # Button mappings
    button_mappings: Optional[Dict[int, str]] = None
    
    # Advanced settings
    force_feedback_enabled: bool = True
    auto_center_strength: float = 0.5
    
    def __post_init__(self):
        if self.button_mappings is None:
            self.button_mappings = {
                0: 'space',     # X button - usually space/handbrake
                1: 'space',     # Square button - handbrake (alternative)
                2: 'c',         # Circle button
                3: 'r',         # Triangle button - look behind
                4: 'e',         # Shift up (right paddle)
                5: 'q',         # Shift down (left paddle)
                6: 'r',         # R2 button
                7: 'f',         # L2 button 
                8: 'tab',       # Share button
                9: 'esc',       # Options button
                10: 'ctrl',     # R3 button
                11: 'shift',    # L3 button
                23: 'f',        # Ignition button
                24: 'esc',      # PlayStation button
            }


class VirtualController:
    """Manages virtual Xbox controller for smooth analog input"""
    
    def __init__(self, config=None):
        self.config = config
        self.gamepad = None
        self.connected = False
        
        # Track current values for display
        self.current_left_x = 0.0
        self.current_left_y = 0.0
        self.current_right_x = 0.0
        self.current_right_y = 0.0
        self.current_left_trigger = 0.0
        self.current_right_trigger = 0.0
        
        if VGAMEPAD_AVAILABLE:
            try:
                self.gamepad = vg.VX360Gamepad()
                self.connected = True
                print("✅ Virtual Xbox controller created successfully")
            except Exception as e:
                print(f"❌ Failed to create virtual controller: {e}")
                self.connected = False
        else:
            print("❌ vgamepad not available - install with: pip install vgamepad")
    
    def update_steering(self, steering_value: float):
        """Update steering value for virtual controller stick(s)"""
        if not self.connected:
            return
        try:
            steering_value = max(-1.0, min(1.0, steering_value))
            stick_mode = self.config.controller_stick_mode if self.config else "left"
            if stick_mode == "left":
                self.current_left_x = steering_value
            elif stick_mode == "right":
                self.current_right_x = steering_value
            # Only update one stick, not both
            self.apply_stick_outputs()
        except Exception as e:
            print(f"Error updating virtual controller steering: {e}")
    
    def update_throttle_brake(self, throttle: float, brake: float):
        """Update throttle/brake value for virtual controller stick(s)"""
        if not self.connected:
            return
        try:
            throttle_axis = self.config.controller_throttle_axis if self.config else "triggers"
            if throttle_axis == "triggers":
                # Invert triggers: 0 = fully pressed, 1 = not pressed
                throttle_trigger = int(max(0, min(1, 1 - throttle)) * 255)
                brake_trigger = int(max(0, min(1, 1 - brake)) * 255)
                self.gamepad.right_trigger(value=throttle_trigger)
                self.gamepad.left_trigger(value=brake_trigger)
                self.current_right_trigger = throttle
                self.current_left_trigger = brake
                print(f"Virtual Xbox Throttle: {throttle:.3f} ({throttle_trigger}), Brake: {brake:.3f} ({brake_trigger})")
            else:
                # Analog axis: axis_value = throttle and brake are independent
                axis_throttle = max(-1.0, min(1.0, throttle))
                axis_brake = max(-1.0, min(1.0, brake))
                if throttle_axis == "left_x":
                    self.current_left_x = axis_throttle
                elif throttle_axis == "left_y":
                    self.current_left_y = axis_throttle
                elif throttle_axis == "right_x":
                    self.current_right_x = axis_brake
                elif throttle_axis == "right_y":
                    self.current_right_y = axis_brake
                print(f"Virtual Xbox Axis ({throttle_axis}): throttle={axis_throttle:.3f}, brake={axis_brake:.3f}")
            self.apply_stick_outputs()
        except Exception as e:
            print(f"Error updating virtual controller pedals: {e}")
    def apply_stick_outputs(self):
        stick_mode = self.config.controller_stick_mode if self.config else "left"
        # Left stick
        x = int(self.current_left_x * 32767)
        y = int(self.current_left_y * 32767)
        if stick_mode == "left":
            self.gamepad.left_joystick(x_value=x, y_value=y)
        else:
            self.gamepad.left_joystick(x_value=0, y_value=0)
        # Right stick
        x_r = int(self.current_right_x * 32767)
        y_r = int(self.current_right_y * 32767)
        if stick_mode == "right":
            self.gamepad.right_joystick(x_value=x_r, y_value=y_r)
        else:
            self.gamepad.right_joystick(x_value=0, y_value=0)
        self.gamepad.update()
    
    def press_button(self, button: str):
        """Press a virtual controller button"""
        if not self.connected:
            return
        
        try:
            button_map = {
                'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                'b': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                'x': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                'y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                'lb': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                'rb': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                'start': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
                'back': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            }
            
            if button in button_map:
                self.gamepad.press_button(button_map[button])
                self.gamepad.update()
        except Exception as e:
            print(f"Error pressing virtual controller button: {e}")
    
    def release_button(self, button: str):
        """Release a virtual controller button"""
        if not self.connected:
            return
        
        try:
            button_map = {
                'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                'b': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                'x': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                'y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                'lb': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                'rb': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                'start': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
                'back': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            }
            
            if button in button_map:
                self.gamepad.release_button(button_map[button])
                self.gamepad.update()
        except Exception as e:
            print(f"Error releasing virtual controller button: {e}")
    
    def test_controller(self):
        """Test virtual controller with sample inputs"""
        if not self.connected:
            print("Virtual controller not connected")
            return False
            
        try:
            # Test steering
            print("Testing virtual controller...")
            self.gamepad.left_joystick(x_value=16000, y_value=0)  # Half right
            self.gamepad.update()
            time.sleep(0.1)
            
            self.gamepad.left_joystick(x_value=-16000, y_value=0)  # Half left  
            self.gamepad.update()
            time.sleep(0.1)
            
            self.gamepad.left_joystick(x_value=0, y_value=0)  # Center
            self.gamepad.update()
            
            print("Virtual controller test completed")
            return True
        except Exception as e:
            print(f"Virtual controller test failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect virtual controller"""
        if self.connected and self.gamepad:
            try:
                # Reset all inputs to neutral
                self.gamepad.left_joystick(x_value=0, y_value=0)
                self.gamepad.right_joystick(x_value=0, y_value=0)
                self.gamepad.left_trigger(value=0)
                self.gamepad.right_trigger(value=0)
                self.gamepad.update()
                self.connected = False
            except Exception as e:
                print(f"Error disconnecting virtual controller: {e}")


class EnhancedG29Controller:
    """Enhanced G29 controller with multiple control modes"""
    
    def __init__(self, config: WheelConfig):
        self.config = config
        self.wheel = None
        self.running = False
        
        # Input controllers
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()
        self.virtual_controller = VirtualController(config)
        
        # State tracking
        self.current_keys_pressed = set()
        self.current_mouse_x = 0
        self.last_steering_value = 0.0
        
        # LFO timing for keyboard steering
        self.last_lfo_time = 0.0
        self.lfo_state = False  # True = key pressed, False = key released
        
        # Wheel state
        self.steering_angle = 0.0
        self.throttle_value = 0.0
        self.brake_value = 0.0
        self.clutch_value = 0.0
        self.button_states = {}
        self.dpad_states = {}  # Track D-pad states
        
        pygame.init()
        pygame.joystick.init()
        
        print(f"Control mode: {self.config.control_mode}")
        if self.config.control_mode == ControlMode.VIRTUAL_XBOX.value and not self.virtual_controller.connected:
            print("⚠️  Virtual Xbox mode requested but not available, falling back to mouse steering")
            self.config.control_mode = ControlMode.MOUSE_STEERING.value
    
    def find_g29(self) -> bool:
        """Find and initialize the G29 wheel"""
        joystick_count = pygame.joystick.get_count()
        
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            name = joystick.get_name().lower()
            
            if 'g29' in name or 'logitech' in name:
                self.wheel = joystick
                print(f"Found G29 wheel: {joystick.get_name()}")
                print(f"Axes: {joystick.get_numaxes()}")
                print(f"Buttons: {joystick.get_numbuttons()}")
                print(f"Hats: {joystick.get_numhats()}")
                return True
                
        return False
    
    def is_roblox_active(self) -> bool:
        """Check if Roblox window is currently active"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd).lower()
            return 'roblox' in window_title
        except:
            return False
    
    def apply_deadzone(self, value: float, deadzone: float) -> float:
        """Apply deadzone to analog input"""
        if abs(value) < deadzone:
            return 0.0
        
        # Scale the remaining range
        if value > 0:
            return (value - deadzone) / (1.0 - deadzone)
        else:
            return (value + deadzone) / (1.0 - deadzone)
    
    def apply_steering_range(self, steering_value: float) -> float:
        """Always use full wheel range for max realism. Joystick only maxes out at full wheel lock (-1 or 1)."""
        return steering_value
    
    def smooth_value(self, current: float, target: float, smoothing: float = 0.1) -> float:
        """Apply smoothing to reduce jitter"""
        return current + (target - current) * smoothing
    
    def handle_steering_keyboard(self, steering_value: float):
        """Handle steering using keyboard A/D keys with LFO-style rapid tapping"""
        steering_value = self.apply_deadzone(steering_value, self.config.steering_deadzone)
        steering_value = self.apply_steering_range(steering_value)
        steering_value *= self.config.steering_sensitivity
        
        # Very small deadzone for keyboard mode (much smaller than before)
        if abs(steering_value) < 0.02:  # Much smaller deadzone
            # In actual deadzone - release steering keys only
            self.release_key('a')
            self.release_key('d')
            # Do NOT release throttle/brake keys here
            return
        
        if self.config.keyboard_steering_lfo:
            # LFO-style rapid tapping based on steering angle
            current_time = time.time()
            
            # Calculate tap frequency based on steering intensity
            # More steering = faster tapping for quicker response
            base_frequency = self.config.keyboard_steering_frequency
            intensity = abs(steering_value)
            frequency = base_frequency * (0.5 + intensity * 1.5)  # 0.5x to 2x frequency
            
            # Calculate time between taps
            period = 1.0 / frequency
            
            # Check if it's time to toggle the key state
            if current_time - self.last_lfo_time >= period:
                self.last_lfo_time = current_time
                self.lfo_state = not self.lfo_state
                
                if self.lfo_state:
                    # Press the appropriate key
                    if steering_value > 0:
                        self.press_key('d')
                        self.release_key('a')
                    else:
                        self.press_key('a')
                        self.release_key('d')
                else:
                    # Release steering keys only for the "tap" effect
                    self.release_key('a')
                    self.release_key('d')
        else:
            # Original constant key press method
            if steering_value > 0:
                self.press_key('d')
                self.release_key('a')
            else:
                self.press_key('a')
                self.release_key('d')
    
    def handle_steering_mouse(self, steering_value: float):
        """Handle steering using smooth mouse movement"""
        steering_value = self.apply_deadzone(steering_value, self.config.steering_deadzone)
        steering_value = self.apply_steering_range(steering_value)
        
        if self.config.invert_mouse_steering:
            steering_value = -steering_value
        
        # Calculate mouse movement
        target_movement = steering_value * self.config.mouse_sensitivity
        
        # Apply smoothing
        smooth_movement = self.smooth_value(self.last_steering_value, target_movement, 0.3)
        self.last_steering_value = smooth_movement
        
        # Move mouse with better error handling
        if abs(smooth_movement) > 0.1:
            mouse_delta = int(smooth_movement * 10)
            try:
                if hasattr(self, 'mouse_controller') and self.mouse_controller:
                    self.mouse_controller.move(mouse_delta, 0)
                    print(f"Mouse steering: {steering_value:.3f} -> delta: {mouse_delta}")
                else:
                    print("Mouse controller not available")
            except Exception as e:
                print(f"Mouse movement error: {e}")
        
        # Optional: Return mouse to center when not steering
        elif self.config.mouse_return_center and abs(steering_value) < 0.05:
            self.last_steering_value *= self.config.mouse_return_speed
    
    def handle_steering_virtual_xbox(self, steering_value: float):
        """Handle steering using virtual Xbox controller"""
        steering_value = self.apply_deadzone(steering_value, self.config.steering_deadzone)
        steering_value = self.apply_steering_range(steering_value)
        steering_value *= self.config.controller_steering_range
        
        # Clamp to valid range
        steering_value = max(-1.0, min(1.0, steering_value))
        
        # Debug output for troubleshooting
        if abs(steering_value) > 0.1:
            print(f"Virtual Xbox Steering - Input: {steering_value:.3f}, Deadzone: {self.config.steering_deadzone}, Range: {self.config.steering_range_degrees}°, Stick Mode: {self.config.controller_stick_mode}")
        
        if not self.virtual_controller.connected:
            print("⚠️ Virtual controller not connected!")
            return
            
        self.virtual_controller.update_steering(steering_value)
    
    def handle_steering(self, steering_value: float):
        """Route steering to appropriate handler based on control mode"""
        if not self.is_roblox_active():
            return
        
        if self.config.control_mode == ControlMode.KEYBOARD.value:
            self.handle_steering_keyboard(steering_value)
        elif self.config.control_mode in [ControlMode.MOUSE_STEERING.value, ControlMode.HYBRID.value]:
            self.handle_steering_mouse(steering_value)
        elif self.config.control_mode == ControlMode.VIRTUAL_XBOX.value:
            self.handle_steering_virtual_xbox(steering_value)
    
    def handle_pedals_keyboard(self, throttle: float, brake: float):
        """Handle pedals using keyboard keys"""
        # Handle throttle
        if throttle > 0.1:
            self.press_key(self.config.throttle_key)
        else:
            self.release_key(self.config.throttle_key)
        # Handle brake
        if brake > 0.1:
            self.press_key(self.config.brake_key)
        else:
            self.release_key(self.config.brake_key)
        # Do NOT release steering keys here
    
    def handle_pedals_virtual_xbox(self, throttle: float, brake: float):
        """Handle pedals using virtual Xbox controller based on configured mode"""
        # Always send throttle/brake as left stick Y for virtual controller
        self.virtual_controller.update_throttle_brake(throttle, brake)
    
    def handle_pedals(self, throttle: float, brake: float, clutch: float):
        """Handle throttle, brake, and clutch pedals"""
        if not self.is_roblox_active():
            return

        # Normalize pedal values (G29 pedals: -1 = fully pressed, 1 = not pressed)
        # Invert so that -1 = 1 (fully pressed), 1 = 0 (not pressed)
        throttle = (throttle + 1) / 2
        brake = (brake + 1) / 2
        clutch = (clutch + 1) / 2

        if self.config.control_mode == ControlMode.VIRTUAL_XBOX.value:
            self.handle_pedals_virtual_xbox(throttle, brake)
        else:
            # Use keyboard for pedals in all other modes
            self.handle_pedals_keyboard(throttle, brake)
    
    def press_key(self, key_str: str):
        """Press a key if it's not already pressed"""
        if key_str not in self.current_keys_pressed:
            try:
                if key_str == 'space':
                    key_obj = Key.space
                elif key_str == 'ctrl':
                    key_obj = Key.ctrl
                elif key_str == 'shift':
                    key_obj = Key.shift
                elif key_str == 'tab':
                    key_obj = Key.tab
                elif key_str == 'esc':
                    key_obj = Key.esc
                elif key_str == 'enter':
                    key_obj = Key.enter
                else:
                    key_obj = key_str
                
                self.keyboard_controller.press(key_obj)
                self.current_keys_pressed.add(key_str)
            except Exception as e:
                print(f"Error pressing key {key_str}: {e}")
    
    def release_key(self, key_str: str):
        """Release a key if it's currently pressed"""
        if key_str in self.current_keys_pressed:
            try:
                if key_str == 'space':
                    key_obj = Key.space
                elif key_str == 'ctrl':
                    key_obj = Key.ctrl
                elif key_str == 'shift':
                    key_obj = Key.shift
                elif key_str == 'tab':
                    key_obj = Key.tab
                elif key_str == 'esc':
                    key_obj = Key.esc
                elif key_str == 'enter':
                    key_obj = Key.enter
                else:
                    key_obj = key_str
                
                self.keyboard_controller.release(key_obj)
                self.current_keys_pressed.discard(key_str)
            except Exception as e:
                print(f"Error releasing key {key_str}: {e}")
    
    def handle_dpad(self):
        """Handle D-pad inputs"""
        if not self.wheel or not self.is_roblox_active():
            return
        
        # G29 D-pad is usually hat 0
        for hat_id in range(self.wheel.get_numhats()):
            hat_value = self.wheel.get_hat(hat_id)
            
            # Map D-pad directions to keys
            dpad_mappings = {
                'up': '1',      # D-pad up - gear 1 or camera
                'down': '2',    # D-pad down - gear 2 or camera
                'left': '3',    # D-pad left - gear 3 or turn signal
                'right': '4',   # D-pad right - gear 4 or turn signal
            }
            
            # Check each direction
            current_dpad = {
                'up': hat_value[1] == 1,
                'down': hat_value[1] == -1,
                'left': hat_value[0] == -1,
                'right': hat_value[0] == 1,
            }
            
            for direction, pressed in current_dpad.items():
                was_pressed = self.dpad_states.get(f"{hat_id}_{direction}", False)
                
                if pressed and not was_pressed:
                    # D-pad direction just pressed
                    key = dpad_mappings[direction]
                    self.press_key(key)
                    print(f"D-pad {direction} pressed -> {key}")
                elif not pressed and was_pressed:
                    # D-pad direction just released
                    key = dpad_mappings[direction]
                    self.release_key(key)
                
                self.dpad_states[f"{hat_id}_{direction}"] = pressed

    def handle_buttons(self):
        """Handle wheel button presses"""
        if not self.wheel or not self.is_roblox_active() or not self.config.button_mappings:
            return
            
        for button_id in range(self.wheel.get_numbuttons()):
            button_pressed = self.wheel.get_button(button_id)
            was_pressed = self.button_states.get(button_id, False)
            
            if button_pressed and not was_pressed:
                # Button just pressed
                if button_id in self.config.button_mappings:
                    key = self.config.button_mappings[button_id]
                    if self.config.control_mode == ControlMode.VIRTUAL_XBOX.value:
                        # Map to virtual controller buttons
                        xbox_button_map = {
                            'x': 'x', 'a': 'a', 'b': 'b', 'y': 'y',
                            'lb': 'lb', 'rb': 'rb', 'start': 'start', 'back': 'back'
                        }
                        if key in xbox_button_map:
                            self.virtual_controller.press_button(xbox_button_map[key])
                        else:
                            self.press_key(key)
                    else:
                        self.press_key(key)
                    print(f"Button {button_id} pressed -> {key}")
            elif not button_pressed and was_pressed:
                # Button just released
                if button_id in self.config.button_mappings:
                    key = self.config.button_mappings[button_id]
                    if self.config.control_mode == ControlMode.VIRTUAL_XBOX.value:
                        xbox_button_map = {
                            'x': 'x', 'a': 'a', 'b': 'b', 'y': 'y',
                            'lb': 'lb', 'rb': 'rb', 'start': 'start', 'back': 'back'
                        }
                        if key in xbox_button_map:
                            self.virtual_controller.release_button(xbox_button_map[key])
                        else:
                            self.release_key(key)
                    else:
                        self.release_key(key)
            
            self.button_states[button_id] = button_pressed
    
    def update(self):
        """Main update loop for wheel input processing"""
        if not self.wheel:
            return
        
        pygame.event.pump()
        
        # Get steering wheel input (usually axis 0)
        if self.wheel.get_numaxes() > 0:
            steering = self.wheel.get_axis(0)
            self.steering_angle = steering
            self.handle_steering(steering)
        
        # Get pedal inputs (usually axes 1, 2, 3)
        throttle = 0.0
        brake = 0.0
        clutch = 0.0
        
        if self.wheel.get_numaxes() > 1:
            throttle = self.wheel.get_axis(1)
        if self.wheel.get_numaxes() > 2:
            brake = self.wheel.get_axis(2)
        if self.wheel.get_numaxes() > 3:
            clutch = self.wheel.get_axis(3)
        
        # Store the corrected/inverted values for display (G29 pedals: -1 = pressed, 1 = not pressed)
        throttle_display = (1 - throttle) / 2  # Convert to 0 = not pressed, 1 = fully pressed
        brake_display = (1 - brake) / 2
        clutch_display = (1 - clutch) / 2
        
        # Apply brake/clutch swap if enabled
        if self.config.swap_brake_clutch:
            # Swap brake and clutch for both processing and display
            brake, clutch = clutch, brake
            brake_display, clutch_display = clutch_display, brake_display
        
        # Store display values
        self.throttle_value = throttle_display
        self.brake_value = brake_display
        self.clutch_value = clutch_display
        
        self.handle_pedals(throttle, brake, clutch)
        self.handle_buttons()
        self.handle_dpad()
    
    def start(self):
        """Start the wheel input processing"""
        if not self.find_g29():
            raise Exception("G29 wheel not found! Please ensure it's connected and drivers are installed.")
        
        self.running = True
        mode_names = {
            ControlMode.KEYBOARD.value: "Keyboard Mode (A/D keys)",
            ControlMode.MOUSE_STEERING.value: "Mouse Steering Mode (Smooth analog)",
            ControlMode.VIRTUAL_XBOX.value: "Virtual Xbox Controller Mode",
            ControlMode.HYBRID.value: "Hybrid Mode (Mouse + Keyboard)"
        }
        
        print(f"🎮 G29 controller started in {mode_names.get(self.config.control_mode, 'Unknown')} mode")
        print("Make sure Roblox is the active window to receive inputs.")
        
        while self.running:
            try:
                self.update()
                time.sleep(0.016)  # ~60 FPS
            except Exception as e:
                print(f"Error in wheel update: {e}")
                time.sleep(0.1)
    
    def stop(self):
        """Stop the wheel input processing"""
        self.running = False
        
        # Release all currently pressed keys
        for key in list(self.current_keys_pressed):
            self.release_key(key)
        
        # Disconnect virtual controller
        self.virtual_controller.disconnect()
        
        if self.wheel:
            self.wheel.quit()
        
        pygame.quit()


class ConfigManager:
    """Manages configuration saving and loading"""
    
    def __init__(self, config_file: str = "g29_config.json"):
        self.config_file = config_file
    
    def save_config(self, config: WheelConfig):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(config), f, indent=2)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def load_config(self) -> WheelConfig:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return WheelConfig(**data)
        except Exception as e:
            print(f"Error loading configuration: {e}")
        
        # Return default configuration
        return WheelConfig()


class EnhancedG29GUI:
    """Enhanced GUI with multiple control modes"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("G29 to Roblox Interface - Enhanced")
        self.root.geometry("700x600")
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.controller = None
        self.controller_thread = None
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the enhanced GUI elements"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Control tab
        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text="Control")
        self.setup_control_tab(control_frame)
        
        # Configuration tab
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        self.setup_config_tab(config_frame)
        
        # Status tab
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="Status")
        self.setup_status_tab(status_frame)
    
    def setup_control_tab(self, parent):
        """Setup the main control tab"""
        # Title
        title_label = ttk.Label(parent, text="G29 to Roblox Interface - Enhanced", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Control mode selection
        mode_frame = ttk.LabelFrame(parent, text="Control Mode")
        mode_frame.pack(fill='x', padx=20, pady=10)
        
        self.control_mode_var = tk.StringVar(value=self.config.control_mode)
        
        mode_descriptions = [
            (ControlMode.MOUSE_STEERING.value, "Mouse Steering (Recommended)", "Smooth analog steering via mouse movement"),
            (ControlMode.VIRTUAL_XBOX.value, "Virtual Xbox Controller", "Creates virtual gamepad for native controller support"),
            (ControlMode.KEYBOARD.value, "Keyboard Mode", "A/D keys for steering (less smooth)"),
            (ControlMode.HYBRID.value, "Hybrid Mode", "Mouse steering + keyboard pedals"),
        ]
        
        for i, (mode, title, desc) in enumerate(mode_descriptions):
            frame = ttk.Frame(mode_frame)
            frame.pack(fill='x', padx=5, pady=2)
            
            radio = ttk.Radiobutton(frame, text=title, variable=self.control_mode_var, value=mode)
            radio.pack(anchor='w')
            
            desc_label = ttk.Label(frame, text=desc, font=('Arial', 8), foreground='gray')
            desc_label.pack(anchor='w', padx=20)
            
            # Add availability info
            if mode == ControlMode.VIRTUAL_XBOX.value and not VGAMEPAD_AVAILABLE:
                unavail_label = ttk.Label(frame, text="Requires vgamepad package", font=('Arial', 8), foreground='red')
                unavail_label.pack(anchor='w', padx=20)
        
        # Status label
        self.status_label = ttk.Label(parent, text="Status: Stopped", font=('Arial', 12))
        self.status_label.pack(pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=20)
        
        self.start_button = ttk.Button(button_frame, text="Start Interface", command=self.start_interface)
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Interface", command=self.stop_interface, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        self.test_controller_button = ttk.Button(button_frame, text="Test Virtual Controller", command=self.test_virtual_controller)
        self.test_controller_button.pack(side='left', padx=5)
        
    instructions = """
        """
        
        instructions_label = ttk.Label(parent, text=instructions, justify='left', wraplength=600)
        instructions_label.pack(pady=20, padx=20)
    
    def setup_config_tab(self, parent):
        """Setup the enhanced configuration tab"""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Steering settings
        steering_frame = ttk.LabelFrame(scrollable_frame, text="Steering Settings")
        steering_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(steering_frame, text="Steering Sensitivity:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.steering_sens_var = tk.DoubleVar(value=self.config.steering_sensitivity)
        steering_scale = ttk.Scale(steering_frame, from_=0.1, to=3.0, variable=self.steering_sens_var, orient='horizontal')
        steering_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(steering_frame, text="Steering Deadzone:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.deadzone_var = tk.DoubleVar(value=self.config.steering_deadzone)
        deadzone_scale = ttk.Scale(steering_frame, from_=0.0, to=0.2, variable=self.deadzone_var, orient='horizontal')
        deadzone_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(steering_frame, text="Steering Range (degrees):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.steering_range_var = tk.DoubleVar(value=self.config.steering_range_degrees)
        steering_range_scale = ttk.Scale(steering_frame, from_=180, to=900, variable=self.steering_range_var, orient='horizontal')
        steering_range_scale.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        # Add value display labels
        self.sens_value_label = ttk.Label(steering_frame, text=f"{self.config.steering_sensitivity:.1f}")
        self.sens_value_label.grid(row=0, column=2, padx=5, pady=2)
        
        self.deadzone_value_label = ttk.Label(steering_frame, text=f"{self.config.steering_deadzone:.2f}")
        self.deadzone_value_label.grid(row=1, column=2, padx=5, pady=2)
        
        self.range_value_label = ttk.Label(steering_frame, text=f"{self.config.steering_range_degrees:.0f}°")
        self.range_value_label.grid(row=2, column=2, padx=5, pady=2)
        
        # Bind update functions to show current values
        def update_sens_label(*args):
            self.sens_value_label.config(text=f"{self.steering_sens_var.get():.1f}")
        
        def update_deadzone_label(*args):
            self.deadzone_value_label.config(text=f"{self.deadzone_var.get():.2f}")
        
        def update_range_label(*args):
            self.range_value_label.config(text=f"{self.steering_range_var.get():.0f}°")
        
        self.steering_sens_var.trace_add('write', update_sens_label)
        self.deadzone_var.trace_add('write', update_deadzone_label)
        self.steering_range_var.trace_add('write', update_range_label)
        
        steering_frame.columnconfigure(1, weight=1)
        
        # Mouse-specific settings
        mouse_frame = ttk.LabelFrame(scrollable_frame, text="Mouse Steering Settings")
        mouse_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(mouse_frame, text="Mouse Sensitivity:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.mouse_sens_var = tk.DoubleVar(value=self.config.mouse_sensitivity)
        mouse_scale = ttk.Scale(mouse_frame, from_=0.5, to=10.0, variable=self.mouse_sens_var, orient='horizontal')
        mouse_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        self.invert_mouse_var = tk.BooleanVar(value=self.config.invert_mouse_steering)
        invert_check = ttk.Checkbutton(mouse_frame, text="Invert Mouse Steering", variable=self.invert_mouse_var)
        invert_check.grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        self.mouse_return_var = tk.BooleanVar(value=self.config.mouse_return_center)
        return_check = ttk.Checkbutton(mouse_frame, text="Auto-center Mouse", variable=self.mouse_return_var)
        return_check.grid(row=2, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        mouse_frame.columnconfigure(1, weight=1)
        
        # Key mapping settings
        key_frame = ttk.LabelFrame(scrollable_frame, text="Key Mappings (Keyboard/Hybrid Mode)")
        key_frame.pack(fill='x', padx=10, pady=5)
        
        self.key_vars = {}
        key_mappings = [
            ("Throttle", "throttle_key"),
            ("Brake", "brake_key"),
            ("Handbrake", "handbrake_key"),
            ("Horn", "horn_key")
        ]
        
        for i, (label, attr) in enumerate(key_mappings):
            ttk.Label(key_frame, text=f"{label}:").grid(row=i, column=0, sticky='w', padx=5, pady=2)
            var = tk.StringVar(value=getattr(self.config, attr))
            self.key_vars[attr] = var
            entry = ttk.Entry(key_frame, textvariable=var, width=10)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=2)
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="Advanced Settings")
        advanced_frame.pack(fill='x', padx=10, pady=5)
        
        # Keyboard Steering LFO settings
        ttk.Label(advanced_frame, text="Keyboard Steering Mode:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.lfo_mode_var = tk.BooleanVar(value=self.config.keyboard_steering_lfo)
        lfo_check = ttk.Checkbutton(advanced_frame, text="Use LFO (rapid tapping)", variable=self.lfo_mode_var)
        lfo_check.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(advanced_frame, text="LFO Frequency (Hz):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.lfo_freq_var = tk.DoubleVar(value=self.config.keyboard_steering_frequency)
        lfo_freq_scale = ttk.Scale(advanced_frame, from_=5.0, to=30.0, variable=self.lfo_freq_var, orient='horizontal')
        lfo_freq_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        self.lfo_freq_value_label = ttk.Label(advanced_frame, text=f"{self.config.keyboard_steering_frequency:.1f} Hz")
        self.lfo_freq_value_label.grid(row=1, column=2, padx=5, pady=2)
        
        def update_lfo_freq_label(*args):
            self.lfo_freq_value_label.config(text=f"{self.lfo_freq_var.get():.1f} Hz")
        
        self.lfo_freq_var.trace_add('write', update_lfo_freq_label)
        
        # Pedal swap setting
        self.pedal_swap_var = tk.BooleanVar(value=self.config.swap_brake_clutch)
        pedal_swap_check = ttk.Checkbutton(advanced_frame, text="Swap Brake & Clutch Pedals", variable=self.pedal_swap_var)
        pedal_swap_check.grid(row=2, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        # Virtual Controller Stick Mode
        ttk.Label(advanced_frame, text="Virtual Controller Stick (Steering):").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.stick_mode_var = tk.StringVar(value=self.config.controller_stick_mode)
        stick_mode_frame = ttk.Frame(advanced_frame)
        stick_mode_frame.grid(row=3, column=1, sticky='w', padx=5, pady=2)
        ttk.Radiobutton(stick_mode_frame, text="Left Stick", variable=self.stick_mode_var, value="left").pack(side='left', padx=5)
        ttk.Radiobutton(stick_mode_frame, text="Right Stick", variable=self.stick_mode_var, value="right").pack(side='left', padx=5)
        
        # Virtual Controller Throttle/Brake Axis
        ttk.Label(advanced_frame, text="Throttle/Brake Axis:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.throttle_axis_var = tk.StringVar(value=self.config.controller_throttle_axis)
        throttle_axis_frame = ttk.Frame(advanced_frame)
        throttle_axis_frame.grid(row=4, column=1, sticky='w', padx=5, pady=2)
        ttk.Radiobutton(throttle_axis_frame, text="Left Stick X", variable=self.throttle_axis_var, value="left_x").pack(side='left', padx=5)
        ttk.Radiobutton(throttle_axis_frame, text="Left Stick Y", variable=self.throttle_axis_var, value="left_y").pack(side='left', padx=5)
        ttk.Radiobutton(throttle_axis_frame, text="Right Stick X", variable=self.throttle_axis_var, value="right_x").pack(side='left', padx=5)
        ttk.Radiobutton(throttle_axis_frame, text="Right Stick Y", variable=self.throttle_axis_var, value="right_y").pack(side='left', padx=5)
        ttk.Radiobutton(throttle_axis_frame, text="Triggers (RT/LT)", variable=self.throttle_axis_var, value="triggers").pack(side='left', padx=5)
        
        # Save button
        save_button = ttk.Button(scrollable_frame, text="Save Configuration", command=self.save_config)
        save_button.pack(pady=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_status_tab(self, parent):
        """Setup the status monitoring tab with visual steering wheel"""
        # Create main frame with visual and text sections
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left side - Visual indicators
        visual_frame = ttk.LabelFrame(main_frame, text="Visual Indicators")
        visual_frame.pack(side='left', fill='both', expand=False, padx=(0, 10))
        
        # Steering wheel canvas
        wheel_frame = ttk.LabelFrame(visual_frame, text="Steering Wheel")
        wheel_frame.pack(fill='x', padx=5, pady=5)
        
        self.wheel_canvas = tk.Canvas(wheel_frame, width=200, height=200, bg='black')
        self.wheel_canvas.pack(padx=10, pady=10)
        
        # Force feedback frame
        ff_frame = ttk.LabelFrame(visual_frame, text="Force Feedback")
        ff_frame.pack(fill='x', padx=5, pady=5)

        # Force feedback meter (placeholder for now)
        self.ff_canvas = tk.Canvas(ff_frame, width=200, height=60, bg='black')
        self.ff_canvas.pack(padx=10, pady=10)

        # Virtual Controller frame
        controller_frame = ttk.LabelFrame(visual_frame, text="Virtual Xbox Controller")
        controller_frame.pack(fill='x', padx=5, pady=5)

        # Left and right joystick visualization
        joystick_container = ttk.Frame(controller_frame)
        joystick_container.pack(padx=5, pady=5)

        # Left joystick (steering)
        left_stick_frame = ttk.LabelFrame(joystick_container, text="Left Stick (Steering)")
        left_stick_frame.pack(side='left', padx=5)
        
        self.left_stick_canvas = tk.Canvas(left_stick_frame, width=120, height=120, bg='black')
        self.left_stick_canvas.pack(padx=5, pady=5)
        
        # Left stick coordinates
        self.left_stick_coords = ttk.Label(left_stick_frame, text="X: 0.00, Y: 0.00")
        self.left_stick_coords.pack(pady=2)

        # Right joystick (future use)
        right_stick_frame = ttk.LabelFrame(joystick_container, text="Right Stick (Throttle/Brake)")
        right_stick_frame.pack(side='left', padx=5)
        
        self.right_stick_canvas = tk.Canvas(right_stick_frame, width=120, height=120, bg='black')
        self.right_stick_canvas.pack(padx=5, pady=5)
        
        # Right stick coordinates
        self.right_stick_coords = ttk.Label(right_stick_frame, text="X: 0.00, Y: 0.00")
        self.right_stick_coords.pack(pady=2)

        # Trigger indicators
        trigger_frame = ttk.LabelFrame(controller_frame, text="Triggers")
        trigger_frame.pack(fill='x', padx=5, pady=5)
        
        # Left trigger (brake)
        ttk.Label(trigger_frame, text="Left Trigger (Brake):").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.left_trigger_var = tk.DoubleVar()
        self.left_trigger_bar = ttk.Progressbar(trigger_frame, variable=self.left_trigger_var, maximum=1.0, length=150)
        self.left_trigger_bar.grid(row=0, column=1, padx=5, pady=2)
        self.left_trigger_label = ttk.Label(trigger_frame, text="0.00")
        self.left_trigger_label.grid(row=0, column=2, padx=5, pady=2)
        
        # Right trigger (gas)
        ttk.Label(trigger_frame, text="Right Trigger (Gas):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.right_trigger_var = tk.DoubleVar()
        self.right_trigger_bar = ttk.Progressbar(trigger_frame, variable=self.right_trigger_var, maximum=1.0, length=150)
        self.right_trigger_bar.grid(row=1, column=1, padx=5, pady=2)
        self.right_trigger_label = ttk.Label(trigger_frame, text="0.00")
        self.right_trigger_label.grid(row=1, column=2, padx=5, pady=2)        # Pedal indicators
        pedal_frame = ttk.LabelFrame(visual_frame, text="Pedal Positions")
        pedal_frame.pack(fill='x', padx=5, pady=5)
        
        # Throttle bar
        ttk.Label(pedal_frame, text="Throttle:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.throttle_var = tk.DoubleVar()
        self.throttle_bar = ttk.Progressbar(pedal_frame, variable=self.throttle_var, maximum=1.0, length=150)
        self.throttle_bar.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.throttle_label = ttk.Label(pedal_frame, text="0.000")
        self.throttle_label.grid(row=0, column=2, padx=5, pady=2)
        
        # Brake bar
        ttk.Label(pedal_frame, text="Brake:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.brake_var = tk.DoubleVar()
        self.brake_bar = ttk.Progressbar(pedal_frame, variable=self.brake_var, maximum=1.0, length=150)
        self.brake_bar.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        self.brake_label = ttk.Label(pedal_frame, text="0.000")
        self.brake_label.grid(row=1, column=2, padx=5, pady=2)
        
        # Clutch bar
        ttk.Label(pedal_frame, text="Clutch:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.clutch_var = tk.DoubleVar()
        self.clutch_bar = ttk.Progressbar(pedal_frame, variable=self.clutch_var, maximum=1.0, length=150)
        self.clutch_bar.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        self.clutch_label = ttk.Label(pedal_frame, text="0.000")
        self.clutch_label.grid(row=2, column=2, padx=5, pady=2)
        
        pedal_frame.columnconfigure(1, weight=1)
        
        # Right side - Text status
        text_frame = ttk.LabelFrame(main_frame, text="Detailed Status")
        text_frame.pack(side='right', fill='both', expand=True)
        
        self.status_text = tk.Text(text_frame, height=25, width=50, font=('Consolas', 9))
        self.status_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initialize visual elements
        self.init_visual_elements()
        
        # Update status periodically
        self.update_status()
    
    def init_visual_elements(self):
        """Initialize the visual steering wheel and force feedback displays"""
        # Draw steering wheel base
        self.draw_steering_wheel(0.0)  # Start at center
        
        # Draw force feedback meter base
        self.draw_force_feedback_meter(0.0)  # Start at zero
    
    def draw_steering_wheel(self, steering_angle):
        """Draw steering wheel with current angle"""
        self.wheel_canvas.delete("all")
        
        # Canvas dimensions
        width = 200
        height = 200
        center_x = width // 2
        center_y = height // 2
        radius = 80
        
        # Draw outer wheel circle
        self.wheel_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline='white', width=3, fill='gray20'
        )
        
        # Draw center hub
        hub_radius = 15
        self.wheel_canvas.create_oval(
            center_x - hub_radius, center_y - hub_radius,
            center_x + hub_radius, center_y + hub_radius,
            outline='white', width=2, fill='gray40'
        )
        
        # Convert steering angle to rotation (steering_angle ranges from -1 to 1)
        # Map to degrees: -450 to +450 degrees (900 degree wheel range)
        max_rotation = self.controller.config.steering_range_degrees / 2 if self.controller else 450
        rotation_degrees = steering_angle * max_rotation
        rotation_radians = math.radians(rotation_degrees)
        
        # Draw spokes
        spoke_length = radius - 10
        for i in range(3):  # 3 spokes
            spoke_angle = rotation_radians + (i * 2 * math.pi / 3)
            end_x = center_x + spoke_length * math.cos(spoke_angle - math.pi/2)
            end_y = center_y + spoke_length * math.sin(spoke_angle - math.pi/2)
            
            self.wheel_canvas.create_line(
                center_x, center_y, end_x, end_y,
                fill='yellow', width=4
            )
        
        # Draw top indicator (12 o'clock position rotated with wheel)
        indicator_angle = rotation_radians - math.pi/2
        indicator_x = center_x + (radius - 5) * math.cos(indicator_angle)
        indicator_y = center_y + (radius - 5) * math.sin(indicator_angle)
        
        self.wheel_canvas.create_oval(
            indicator_x - 8, indicator_y - 8,
            indicator_x + 8, indicator_y + 8,
            fill='red', outline='white', width=2
        )
        
        # Draw angle text
        angle_text = f"{rotation_degrees:.1f}°"
        self.wheel_canvas.create_text(
            center_x, height - 20,
            text=angle_text, fill='white', font=('Arial', 12, 'bold')
        )
        
        # Draw range indicator
        range_text = f"Range: {max_rotation*2:.0f}°"
        self.wheel_canvas.create_text(
            center_x, 20,
            text=range_text, fill='cyan', font=('Arial', 10)
        )
    
    def draw_force_feedback_meter(self, ff_strength):
        """Draw force feedback strength meter"""
        self.ff_canvas.delete("all")
        
        width = 200
        height = 60
        
        # Draw background bar
        bar_x = 20
        bar_y = height // 2 - 10
        bar_width = width - 40
        bar_height = 20
        
        self.ff_canvas.create_rectangle(
            bar_x, bar_y, bar_x + bar_width, bar_y + bar_height,
            outline='white', fill='gray20', width=2
        )
        
        # Draw force feedback level (0-1 range)
        if ff_strength > 0:
            fill_width = int(bar_width * abs(ff_strength))
            color = 'orange' if ff_strength < 0.7 else 'red'
            
            self.ff_canvas.create_rectangle(
                bar_x + 2, bar_y + 2,
                bar_x + fill_width - 2, bar_y + bar_height - 2,
                fill=color, outline=''
            )
        
        # Draw center line
        center_x = bar_x + bar_width // 2
        self.ff_canvas.create_line(
            center_x, bar_y, center_x, bar_y + bar_height,
            fill='white', width=1
        )
        
        # Draw labels
        self.ff_canvas.create_text(10, height // 2, text='0%', fill='white', font=('Arial', 8))
        self.ff_canvas.create_text(width - 10, height // 2, text='100%', fill='white', font=('Arial', 8))
        
        # Draw current value
        ff_text = f"Force: {ff_strength*100:.1f}%"
        self.ff_canvas.create_text(
            width // 2, height - 10,
            text=ff_text, fill='white', font=('Arial', 10, 'bold')
        )
    
    def draw_joystick(self, canvas, x_value, y_value, stick_name, is_active=True):
        """Draw a joystick position indicator"""
        canvas.delete("all")
        
        width = 120
        height = 120
        center_x = width // 2
        center_y = height // 2
        radius = 50
        
        # Draw outer circle (joystick range) - color based on active state
        circle_color = 'white' if is_active else 'gray60'
        fill_color = 'gray20' if is_active else 'gray10'
        
        canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline=circle_color, fill=fill_color, width=2
        )
        
        # Draw center crosshairs
        line_color = 'gray50' if is_active else 'gray30'
        canvas.create_line(
            center_x - radius, center_y, center_x + radius, center_y,
            fill=line_color, width=1
        )
        canvas.create_line(
            center_x, center_y - radius, center_x, center_y + radius,
            fill=line_color, width=1
        )
        
        # Draw center dot
        canvas.create_oval(
            center_x - 2, center_y - 2, center_x + 2, center_y + 2,
            fill=line_color, outline=line_color
        )
        
        # Calculate joystick position (-1 to 1 range maps to circle)
        stick_x = center_x + (x_value * radius * 0.9)  # 0.9 to keep within circle
        stick_y = center_y + (y_value * radius * 0.9)  # Y is inverted in canvas
        
        # Draw joystick position - brighter when active
        stick_radius = 8
        if is_active:
            color = 'lime' if stick_name == "Left" else 'cyan'
        else:
            color = 'gray50'
            
        canvas.create_oval(
            stick_x - stick_radius, stick_y - stick_radius,
            stick_x + stick_radius, stick_y + stick_radius,
            fill=color, outline='white' if is_active else 'gray70', width=2
        )
        
        # Draw direction line from center to position
        if abs(x_value) > 0.01 or abs(y_value) > 0.01:
            canvas.create_line(
                center_x, center_y, stick_x, stick_y,
                fill=color, width=2
            )
        
        # Add active/inactive indicator text
        status_text = "ACTIVE" if is_active else "INACTIVE"
        text_color = color if is_active else 'gray50'
        canvas.create_text(
            center_x, height - 10,
            text=status_text, fill=text_color, font=('Arial', 8, 'bold')
        )
    
    def update_virtual_controller_display(self, left_x, left_y, right_x, right_y, left_trigger, right_trigger):
        """Update the virtual controller visual display"""
        if hasattr(self, 'left_stick_canvas'):
            # Get stick mode for visual indication
            stick_mode = self.controller.config.controller_stick_mode if self.controller and self.controller.config else "left"
            
            # Update left joystick with active indication
            left_active = stick_mode in ["left", "both"]
            self.draw_joystick(self.left_stick_canvas, left_x, left_y, "Left", left_active)
            self.left_stick_coords.config(text=f"X: {left_x:.2f}, Y: {left_y:.2f}")
            
            # Update right joystick with active indication
            right_active = stick_mode in ["right", "both"]
            self.draw_joystick(self.right_stick_canvas, right_x, right_y, "Right", right_active)
            self.right_stick_coords.config(text=f"X: {right_x:.2f}, Y: {right_y:.2f}")
            
            # Update triggers
            self.left_trigger_var.set(left_trigger)
            self.left_trigger_label.config(text=f"{left_trigger:.2f}")
            
            self.right_trigger_var.set(right_trigger)
            self.right_trigger_label.config(text=f"{right_trigger:.2f}")

    def update_status(self):
        """Update the status display with enhanced information"""
        if self.controller and self.controller.wheel:
            # Get control mode name
            mode_names = {
                ControlMode.KEYBOARD.value: "Keyboard (A/D keys)",
                ControlMode.MOUSE_STEERING.value: "Mouse Steering (Analog)",
                ControlMode.VIRTUAL_XBOX.value: "Virtual Xbox Controller",
                ControlMode.HYBRID.value: "Hybrid (Mouse + Keyboard)"
            mode_names = {
                ControlMode.KEYBOARD.value: "Keyboard (A/D keys)",
                ControlMode.MOUSE_STEERING.value: "Mouse Steering (Analog)",
                ControlMode.VIRTUAL_XBOX.value: "Virtual Xbox Controller",
                ControlMode.HYBRID.value: "Hybrid (Mouse + Keyboard)"
            }
            mode_name = mode_names.get(self.controller.config.control_mode, "Unknown")
            status_info = f"""
            else:
                status_info += "No buttons pressed\n"
            
            # Control mode specific info
            if self.controller.config.control_mode == ControlMode.MOUSE_STEERING.value:
                status_info += f"\nMouse Settings:\n"
                status_info += f"Sensitivity: {self.controller.config.mouse_sensitivity:.1f}\n"
                status_info += f"Last Movement: {self.controller.last_steering_value:.3f}\n"
            elif self.controller.config.control_mode == ControlMode.VIRTUAL_XBOX.value:
                status_info += f"\nVirtual Controller:\n"
                status_info += f"Connected: {self.controller.virtual_controller.connected}\n"
                status_info += f"Steering Range: {self.controller.config.controller_steering_range:.1f}\n"
                status_info += f"Stick Mode: {self.controller.config.controller_stick_mode}\n"
                status_info += f"Throttle/Brake Axis: {self.controller.config.controller_throttle_axis}\n"
            
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, status_info)
            
            # Update visual elements
            self.draw_steering_wheel(self.controller.steering_angle)
            
            # Update pedal progress bars
            self.throttle_var.set(self.controller.throttle_value)
            self.throttle_label.config(text=f"{self.controller.throttle_value:.3f}")
            
            self.brake_var.set(self.controller.brake_value)
            self.brake_label.config(text=f"{self.controller.brake_value:.3f}")
            
            self.clutch_var.set(self.controller.clutch_value)
            self.clutch_label.config(text=f"{self.controller.clutch_value:.3f}")
            
            # Update force feedback meter (placeholder - G29 doesn't report FF status)
            # For now, show steering effort as a simulation
            ff_simulation = abs(self.controller.steering_angle) * 0.8  # Simulate resistance
            self.draw_force_feedback_meter(ff_simulation)
            
            # Update virtual controller display
            if self.controller.virtual_controller and hasattr(self, 'left_stick_canvas'):
                vc = self.controller.virtual_controller
                self.update_virtual_controller_display(
                    vc.current_left_x, vc.current_left_y,
                    vc.current_right_x, vc.current_right_y,
                    vc.current_left_trigger, vc.current_right_trigger
                )
            
        else:
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, "Wheel Status: Not Connected\n\nPlease start the interface to see live data.")

            # Reset visual elements when not connected
            if hasattr(self, 'wheel_canvas'):
                self.draw_steering_wheel(0.0)
                self.throttle_var.set(0.0)
                self.throttle_label.config(text="0.000")
                self.brake_var.set(0.0)
                self.brake_label.config(text="0.000")
                self.clutch_var.set(0.0)
                self.clutch_label.config(text="0.000")
                self.draw_force_feedback_meter(0.0)
        # Add GitHub link at the bottom of the window
        github_frame = ttk.Frame(self.root)
        github_frame.pack(side='bottom', fill='x', pady=5)
        github_label = ttk.Label(github_frame, text="View on GitHub: ", font=('Arial', 10))
        github_label.pack(side='left')
        def open_github(event=None):
            import webbrowser
            webbrowser.open_new("https://github.com/williamcommu")
        github_link = ttk.Label(github_frame, text="https://github.com/williamcommu", foreground="blue", cursor="hand2", font=('Arial', 10, 'underline'))
        github_link.pack(side='left')
        github_link.bind("<Button-1>", open_github)
        
        # Schedule next update
        self.root.after(100, self.update_status)
    
    def start_interface(self):
        """Start the enhanced G29 interface"""
        try:
            # Update config from GUI
            self.update_config_from_gui()
            
            self.controller = EnhancedG29Controller(self.config)
            
            # Start controller in separate thread
            self.controller_thread = threading.Thread(target=self.controller.start, daemon=True)
            self.controller_thread.start()
            
            mode_names = {
                ControlMode.KEYBOARD.value: "Keyboard Mode",
                ControlMode.MOUSE_STEERING.value: "Mouse Steering Mode", 
                ControlMode.VIRTUAL_XBOX.value: "Virtual Xbox Controller Mode",
                ControlMode.HYBRID.value: "Hybrid Mode"
            }
            
            mode_name = mode_names.get(self.config.control_mode, "Unknown Mode")
            self.status_label.config(text=f"Status: Running ({mode_name})")
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start interface: {e}")
    
    def stop_interface(self):
        """Stop the G29 interface"""
        if self.controller:
            self.controller.stop()
            self.controller = None
        
        self.status_label.config(text="Status: Stopped")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
    
    def update_config_from_gui(self):
        """Update configuration from GUI values"""
        self.config.control_mode = self.control_mode_var.get()
        self.config.steering_sensitivity = self.steering_sens_var.get()
        self.config.steering_deadzone = self.deadzone_var.get()
        self.config.steering_range_degrees = self.steering_range_var.get()
        self.config.mouse_sensitivity = self.mouse_sens_var.get()
        self.config.invert_mouse_steering = self.invert_mouse_var.get()
        self.config.mouse_return_center = self.mouse_return_var.get()
        
        # Advanced settings
        self.config.keyboard_steering_lfo = self.lfo_mode_var.get()
        self.config.keyboard_steering_frequency = self.lfo_freq_var.get()
        self.config.swap_brake_clutch = self.pedal_swap_var.get()
        self.config.controller_stick_mode = self.stick_mode_var.get()
        self.config.controller_throttle_axis = self.throttle_axis_var.get()
        
        for attr, var in self.key_vars.items():
            setattr(self.config, attr, var.get())
    
    def save_config(self):
        """Save current configuration"""
        self.update_config_from_gui()
        self.config_manager.save_config(self.config)
        messagebox.showinfo("Success", "Configuration saved successfully!")
    
    def test_virtual_controller(self):
        """Test virtual controller functionality"""
        try:
            from vgamepad import VX360Gamepad
            import time
            
            # Create a temporary test controller
            test_gamepad = VX360Gamepad()
            
            # Test sequence
            messagebox.showinfo("Virtual Controller Test", 
                "Testing virtual Xbox controller...\nThis will simulate some controller inputs.\n\n" +
                "1. Make sure no game is running\n" +
                "2. You can check Windows Game Controller settings to see the virtual controller\n" +
                "3. Click OK to start test")
            
            # Test steering (left stick)
            print("Testing virtual controller steering...")
            for i in range(5):
                # Right
                test_gamepad.left_joystick(x_value=16000, y_value=0)
                test_gamepad.update()
                time.sleep(0.2)
                
                # Center
                test_gamepad.left_joystick(x_value=0, y_value=0) 
                test_gamepad.update()
                time.sleep(0.1)
                
                # Left  
                test_gamepad.left_joystick(x_value=-16000, y_value=0)
                test_gamepad.update()
                time.sleep(0.2)
                
                # Center
                test_gamepad.left_joystick(x_value=0, y_value=0)
                test_gamepad.update()
                time.sleep(0.1)
            
            # Test triggers
            print("Testing virtual controller triggers...")
            test_gamepad.right_trigger(value=255)  # Full throttle
            test_gamepad.update()
            time.sleep(0.5)
            
            test_gamepad.right_trigger(value=0)    # Release throttle
            test_gamepad.left_trigger(value=255)   # Full brake
            test_gamepad.update()
            time.sleep(0.5)
            
            test_gamepad.left_trigger(value=0)     # Release brake
            test_gamepad.update()
            
            # Reset everything
            test_gamepad.reset()
            test_gamepad.update()
            
            messagebox.showinfo("Test Complete", 
                "Virtual controller test completed!\n\n" +
                "If the virtual controller is working properly:\n" +
                "✅ You should have seen it appear in Windows Game Controllers\n" +
                "✅ Inputs should be detected by controller-aware software\n\n" +
                "If Roblox still doesn't detect steering:\n" +
                "• Try restarting Roblox after starting the interface\n" +
                "• Some games need controller support enabled in settings\n" +
                "• Try Mouse Steering mode as alternative")
            
        except ImportError:
            messagebox.showerror("Error", "vgamepad not installed!\nRun: pip install vgamepad")
        except Exception as e:
            messagebox.showerror("Test Failed", f"Virtual controller test failed:\n{e}")
    
    def run(self):
        """Run the GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Handle window closing"""
        self.stop_interface()
        self.root.destroy()


def main():
    """Main entry point"""
    try:
        # Check if pygame is available
        import pygame
        print("✅ pygame found - wheel support available")
    except ImportError:
        print("❌ ERROR: pygame not found. Please install it with: pip install pygame")
        return
    
    try:
        # Check if pynput is available
        import pynput
        print("✅ pynput found - keyboard/mouse control available")
    except ImportError:
        print("❌ ERROR: pynput not found. Please install it with: pip install pynput")
        return
    
    if VGAMEPAD_AVAILABLE:
        print("✅ vgamepad found - virtual controller support available")
    else:
        print("⚠️ vgamepad not found - virtual controller mode disabled")
        print("   Install with: pip install vgamepad")
    
    print("\n🚀 Starting Enhanced G29 to Roblox Interface...")
    print("🎮 Multiple control modes available for optimal compatibility!")
    print("📡 Make sure your G29 wheel is connected!")
    
    # Start enhanced GUI
    app = EnhancedG29GUI()
    app.run()


if __name__ == "__main__":
    main()
