# SmoothScroll for Windows

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A modern, user-friendly GUI application for smooth scrolling on Windows. This is a fork of the original [Smoothscroll-for-windows](https://github.com/re1von/Smoothscroll-for-windows) by re1von, with significant GUI improvements.

## ✨ Features

- **Smooth Scrolling**: Provides inertial, customizable smooth scrolling for all Windows applications.
- **Graphical User Interface**: Modern, intuitive GUI built with CustomTkinter.
- **Application Exceptions**: Exclude selected applications from smooth scrolling; all other applications use the global parameters.
- **System Tray Integration**: Minimizing hides the window to the tray; left-clicking or double-clicking the tray icon opens it. The app can also start with Windows.
- **Multi-Language Support**: English, Russian, and Chinese.
- **Theme Support**: Light, Dark, and System appearance modes.
- **Autostart**: Option to launch automatically on Windows startup.
- **Configurable Parameters**:
  - Acceleration and deceleration
  - Scroll distance and duration
  - Easing functions
  - Horizontal scroll key modifier
  - Pulse scaling

## 🚀 Installation

### Requirements
- Python 3.11 or higher
- Windows 10/11

### Dependencies
```bash
pip install -r requirements.txt
```

`requirements.txt` installs the runtime and GUI dependencies.

### Building Executable
On Windows, install the runtime dependencies and PyInstaller, then run the build script:
```bash
python -m pip install -r requirements.txt
python -m pip install pyinstaller
build_exe.bat
```

The standalone executable is written to `dist/SmoothScrollGUI.exe`.

## 📖 Usage

### Running the Application
```bash
# GUI Mode (default)
python main.py

# Console Mode
python main.py --console

# Tray Mode (for autostart)
python main.py --tray
```

### GUI Overview

#### Global Settings Tab
Configure default scrolling behavior:
- Distance: Scroll distance in pixels
- Acceleration: Scroll speed multiplier
- Opposite Acceleration: Reverse scroll speed
- Acceleration Delta: Time-based acceleration
- Acceleration Max: Maximum speed limit
- Duration: Animation duration in milliseconds
- Pulse Scale: Animation curve scaling
- Inverted: Reverse scroll direction
- Easing Function: Animation curve type
- Horizontal Scroll Key: Modifier key for horizontal scrolling

#### Applications Tab
Manage the exception list:
- Add an application from the currently visible application picker. Adding it creates an active exception and disables smooth scrolling for that application.
- Turn an exception off to restore global smooth scrolling for that application.
- Delete an exception to restore the global behavior and remove the entry.
- Rebind an entry to another application from its row.

#### App Settings Tab
- Appearance Mode: System/Light/Dark theme
- Language: English/Russian/Chinese. Changing language requires an application restart.
- Autostart: Launch the application minimized to the tray and start the scrolling service with Windows.

#### About Tab
Information about the application, links to source code.

### Configuration
Settings are automatically saved to `config.json` in the application directory.


## 🌍 Localization

The application supports English and Russian languages. Language is saved in configuration and applied on startup.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original project: [Smoothscroll-for-windows](https://github.com/re1von/Smoothscroll-for-windows) by [re1von](https://github.com/re1von)
- GUI Framework: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Easing Functions: [easing-functions](https://github.com/semitable/easing-functions)

## 📞 Support

If you encounter issues or have questions:
1. Check the [Issues](https://github.com/vadenko/Smoothscroll-for-windows/issues) page
2. Create a new issue with detailed information
3. Include your system information and error logs

## 🔄 Changelog

### Version 1.0.0
- Complete GUI overhaul with CustomTkinter
- Multi-language support (EN/RU)
- System tray integration
- Autostart functionality
- Per-application configuration
- Standalone executable build support
