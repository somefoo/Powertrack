



# Powertrack

![image](https://user-images.githubusercontent.com/50917034/227714633-4c37c37d-08c9-4cb0-a246-56ffdd1349b2.png)

An application to track the power usage on your Pinephone (Pro) and estimate the remaining time on battery

## Description

The application provides basic numerical statistics about your battery status. It also provides two graphs. One that displays you your power use and estimated time remaining. The other shows you power usage over the last seconds.

## TLDR, I just want to install it! (PostmarketOS + Phosh)
Clone project and enter project folder of it, then run:
```
sudo apk add meson ninja glib-dev desktop-file-utils
meson build
cd build
ninja
sudo ninja install
```

## Getting Started

### Dependencies

This application has only been tested under PostmarketOS (edge, March 2023) + Phosh. To build the application, ensure the following packages are installed:
```meson ninja glib-dev desktop-file-utils```

### Installing

Build and install the application: `meson build; cd build; sudo ninja install`

### Uninstalling

Go into build folder and run: `sudo ninja uninstall`

### Executing program
The application should now be installed and a new icon should be visible on your app selection screen. Just start it like any other app.
