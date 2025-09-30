### Mouse Steering Mode (Recommended)
- **Smooth analog steering** via mouse movement
- Perfect balance of compatibility and smoothness
- Works with any Roblox game that supports mouse look
- Natural steering feel with analog precision

### Virtual Xbox Controller Mode
- Creates a **real virtual Xbox controller** that Roblox recognizes
- **True analog input** for steering and pedals
- Best compatibility with racing games that support controllers
- Provides native gamepad experience

### Keyboard Mode (Legacy)
- Original A/D key mode for maximum compatibility
- Simple but less smooth than analog modes
- Fallback option for games that don't support analog input

### Hybrid Mode
- Mouse steering + keyboard pedals
- Best of both worlds approach
- Good for games with mixed input support

## Quick Start

### Option 1: Original Interface
Double-click `start.bat` for the original keyboard-only version

## Control Mode Comparison

| Mode | Steering | Pedals | Smoothness | Compatibility |
|------|----------|---------|------------|---------------|
| Mouse | Analog (Mouse) | Digital (Keys) | 5/5 | 4/5 |
| Virtual Xbox | Analog (Joystick) | Analog (Triggers) | 5/5 | 5/5 |
| Keyboard | Digital (A/D) | Digital (W/S) | 2/5 | 5/5 |
| Hybrid | Analog (Mouse) | Digital (Keys) | 4/5 | 4/5 |

## How the New Modes Work

### Mouse Steering Mode
```
G29 Wheel Input -> Smooth Mouse Movement -> Roblox Camera/Steering
```
- Wheel rotation translates to smooth mouse X-axis movement
- Configurable sensitivity and auto-centering
- Pedals still use keyboard (W/S) for maximum compatibility

### Virtual Xbox Controller Mode
```
G29 Wheel Input -> Virtual Xbox Controller -> Roblox Native Gamepad Support
```
- Creates a real virtual Xbox controller in Windows
- Roblox sees it as a genuine gamepad
- Analog steering (left stick) and analog pedals (triggers)
- Full button mapping to Xbox controller buttons

## Enhanced Configuration Options

### Mouse Steering Settings
- **Mouse Sensitivity**: How responsive steering is (0.5 - 10.0)
- **Invert Mouse**: Reverse steering direction if needed
- **Auto-center**: Automatically return to center when not steering
- **Return Speed**: How quickly mouse returns to center

### Virtual Controller Settings
- **Steering Range**: Full analog range control (-1.0 to 1.0)
- **Button Mapping**: Map wheel buttons to Xbox controller buttons
- **Trigger Sensitivity**: Pedal response curves

## Recommended Games & Settings

### For Racing Simulators (Car Dealership Tycoon, Driving Simulator)
**Recommended**: Virtual Xbox Controller Mode
- Most realistic experience
- Full analog control
- Native gamepad support

### For General Roblox Games (Greenville, Bloxburg)
**Recommended**: Mouse Steering Mode
- Great balance of smoothness and compatibility
- Works with most vehicle systems
- Easy to configure

### For Older/Simple Games
**Recommended**: Keyboard Mode
- Maximum compatibility
- Simple and reliable
- Works everywhere

## Real-time Monitoring

The enhanced Status tab shows:
- Visual input bars for all wheel inputs
- Active control mode information
- Mouse movement data (in mouse mode)
- Virtual controller status (in Xbox mode)
- Live key presses and button states

## Advanced Features

### Automatic Mode Detection
- System automatically detects if virtual controller mode is available
- Falls back to mouse mode if vgamepad isn't installed
- Smart compatibility checking

### Smooth Input Processing
- **60 FPS input processing** for responsive control
- **Deadzone handling** to prevent wheel drift
- **Input smoothing** to reduce jitter
- **Sensitivity curves** for fine-tuning

### Multi-threaded Architecture
- Separate thread for wheel input processing
- Non-blocking GUI updates
- Responsive interface even during heavy use

## Troubleshooting New Modes

### Mouse Steering Issues
**"Steering too sensitive"**
- Lower "Mouse Sensitivity" in Configuration tab
- Increase "Steering Deadzone"

**"Mouse doesn't return to center"**
- Enable "Auto-center Mouse" option
- Adjust "Return Speed" setting

### Virtual Xbox Controller Issues
**"Controller mode not available"**
- Install vgamepad: `pip install vgamepad`
- Restart the application

**"Game doesn't recognize controller"**
- Check if game supports Xbox controllers
- Try enabling controller support in game settings
- Some games may need to be restarted after starting virtual controller

## Pro Tips for Smooth Racing

1. **Start with Mouse Mode** - It's the most universally compatible
2. **Test Virtual Xbox Mode** for games that explicitly support controllers
3. **Adjust deadzone** if wheel is too twitchy when centered
4. **Use Status tab** to fine-tune sensitivity settings in real-time
5. **Save different configs** for different games using the save feature

## File Structure

```
wheel/
├── main_enhanced.py        # New enhanced multi-mode interface
├── main.py                 # Original keyboard-only interface
├── start_enhanced.bat      # Launch enhanced version
├── start.bat               # Launch original version
├── test_wheel.bat          # Test wheel connection
├── g29_config.json         # Enhanced configuration file
└── README_enhanced.md      # This file
```

## You Now Have Professional-Grade Wheel Support!

The enhanced interface brings your G29 wheel experience to the next level with:
- True analog steering (no more choppy A/D keys!)
- Multiple compatibility modes
- Professional configuration options
- Real-time monitoring and tuning
- Virtual Xbox controller support

**Next step**: Try `start_enhanced.bat` and experience the difference!

---
*You were absolutely right about analog control being better - this enhanced version provides the smooth, realistic wheel experience you wanted!*
