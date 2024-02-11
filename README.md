# WeeChat Translate Script

## Description
The WeeChat Translate Plugin is a powerful tool designed to enhance your IRC experience by enabling real-time translation of messages for specified channels and servers. This plugin leverages the Google Translate API to provide seamless translation, making it easier to communicate with users from different linguistic backgrounds.

## Features
- Translate incoming and outgoing messages in real-time.
- Configure translation settings for specific channels and servers.
- Support for a wide range of languages.
- Ability to send translated messages with a simple command.

## Installation
1. Ensure you have WeeChat installed on your system.
2. Place the `translate.py` script in your WeeChat Python scripts directory (typically `~/.weechat/python`).
3. Load the script in WeeChat using the command: `/script load translate.py`

## Configuration
Before using the plugin, you need to set your Google Translate API key:
1. Obtain an API key from the [Google Cloud Console](https://console.cloud.google.com/).
2. In WeeChat, set your API key using the command:
/set plugins.var.python.weechat_translate.api_key YOUR_API_KEY


## Usage
The plugin introduces the `/translate` command with several subcommands:

- **list**: Show all channels with translation settings.
- **addin <server> <channel> <target_lang>**: Add a channel to translate incoming messages.
- **addout <server> <channel> <target_lang>**: Add a channel to translate outgoing messages.
- **delin <server> <channel>**: Remove a channel from translating incoming messages.
- **delout <server> <channel>**: Remove a channel from translating outgoing messages.
- **code**: Show available language codes for translation.
- **help**: Show help information for the `/translate` command.

### Sending Translated Messages
To send a translated message, prefix your message with `@<target_lang>`. For example, to send a message in Spanish, type:
@es Your message here.

## Supported Languages
The plugin supports a wide range of languages. Use the `/translate code` command to view all available language codes.

## License
This script is released under the GPL license.

## Author
Jerzy Dabrowski (kofany) - j@dabrowski.biz
