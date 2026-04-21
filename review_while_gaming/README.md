# Review While Gaming

An Anki add-on for studying while playing games or using other applications on your computer.

## Features

### Floating Window

* Displays cards in a window that stays on top of other windows
* Can be dragged and resized with the mouse
* Can be hidden/shown with a keyboard shortcut

### Global Hotkeys

Control Anki even when it’s not in focus:

| Key | Action      |
| --- | ----------- |
| F1  | Again       |
| F2  | Hard        |
| F3  | Good        |
| F4  | Easy        |
| F5  | Show Answer |
| F6  | Play Audio  |

## Installation

1. Download the add-on or clone this repository
2. Copy the `review_while_gaming` folder to the Anki add-ons directory:

   * **Windows**: `%APPDATA%\Anki2\addons21\`
   * **Mac**: `~/Library/Application Support/Anki2/addons21/`
   * **Linux**: `~/.local/share/Anki2/addons21/`
3. Restart Anki

## Configuration

In Anki, go to **Tools > Review While Gaming**:

### SetHotkeys

Configure global hotkeys to control Anki.

### SetFields

Configure the fields displayed in the floating window:

* **Fields**: Card fields separated by commas
* **Background**: Background color (e.g., #1a1a1a)
* **Text color**: Text color (e.g., #ffffff)
* **Font size**: Font size
* **Opacity**: Window opacity (0–1)

### Toggle Mirror

Show/hide the floating window (shortcut: Ctrl+Shift+M)

## Required Permission

On macOS, you need to enable Accessibility permission:

1. Open **System Settings > Privacy & Security > Accessibility**
2. Click the lock to make changes
3. Add Anki to the list of allowed apps

Without this permission, global hotkeys will not work.

## How to Use

1. Start a review session in Anki
2. The floating window will display the current card
3. While gaming, use F1–F4 to answer
4. Use F5 to reveal the answer when needed

## Compatibility

* Anki 2.1.55+
* macOS (requires Accessibility permissions)