# -*- coding: utf-8 -*-
import weechat as w
import json
import requests

SCRIPT_NAME = "inout_translate"
SCRIPT_AUTHOR = "Jerzy Dabrowski (kofany) <j@dabrowski.biz>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC = "Translates messages for specified channels and servers."

TRANSLATE_API_URL = "https://translation.googleapis.com/language/translate/v2"
DETECT_API_URL = "https://translation.googleapis.com/language/translate/v2/detect"

settings = {
    "api_key": "",
    "translate_channels_in": "{}",
    "translate_channels_out": "{}",
}

def get_full_channel_name(channel, server):
    return "{}@{}".format(channel, server)

def translate(text, source_lang, target_lang, api_key):
    params = {
        'q': text,
        'source': source_lang,
        'target': target_lang,
        'format': 'text',
        'key': api_key,
    }
    response = requests.post(TRANSLATE_API_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        return result['data']['translations'][0]['translatedText']
    else:
        w.prnt("", "Translation API error: %s" % response.text)
        return None

def detect_language(text, api_key):
    params = {
        'q': text,
        'key': api_key,
    }
    response = requests.post(DETECT_API_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        return result['data']['detections'][0][0]['language']
    else:
        w.prnt("", "Language detection API error: %s" % response.text)
        return None

def translate_message_if_needed(server, channel, message, api_key):
    full_channel_name = get_full_channel_name(channel, server)
    translate_channels_in = json.loads(w.config_get_plugin("translate_channels_in"))

    if full_channel_name in translate_channels_in:
        target_lang = translate_channels_in[full_channel_name]
        detected_lang = detect_language(message, api_key)
        if detected_lang != target_lang:
            return translate(message, detected_lang, target_lang, api_key)
    return None

def translate_incoming_message_cb(data, modifier, modifier_data, string):
    api_key = w.config_get_plugin("api_key")
    if not api_key:
        w.prnt("", "[Translate Debug] API key is not set.")
        return string

    parsed_data = w.info_get_hashtable("irc_message_parse", {"message": string})
    channel = parsed_data["channel"]
    message = parsed_data["text"]
    server = modifier_data  # Bezpośrednio używamy modifier_data jako nazwę serwera

    translated_message = translate_message_if_needed(server, channel, message, api_key)
    if translated_message:
        # Zastąp oryginalną wiadomość przetłumaczoną, jeśli tłumaczenie jest dostępne
        return string.replace(message, translated_message)
    return string

def translate_outgoing_message_cb(data, modifier, modifier_data, string):
    api_key = w.config_get_plugin("api_key")
    if not api_key:
        return string

    try:
        parts = string.split(' ', 2)
        if len(parts) < 3 or not parts[1].startswith("#"):
            channel = "private"  # Dla wiadomości prywatnych nie mamy kanału
        else:
            channel = parts[1]
        command = parts[0]
        message = parts[2][1:] if parts[1].startswith("#") else " ".join(parts[1:])  # Usuwamy dwukropek z początku wiadomości
    except Exception as e:
        return string

    server = modifier_data
    full_channel_name = get_full_channel_name(channel, server)
    translate_channels_out = json.loads(w.config_get_plugin("translate_channels_out"))

    # Obsługa wiadomości z prefiksem @
    if message.startswith("@"):
        try:
            lang_code, text_to_translate = message[1:].split(' ', 1)
        except ValueError:
            # Niepoprawny format, zwracamy oryginalną wiadomość
            return string
        translated_message = translate(text_to_translate, "", lang_code, api_key)
        if translated_message:
            display_message = "{}{}".format(w.color("cyan"), translated_message)
            w.prnt(w.current_buffer(), display_message)
            return "{} {} :{}".format(command, channel, translated_message)
    elif full_channel_name in translate_channels_out:
        target_lang = translate_channels_out[full_channel_name]
        translated_message = translate(message, "", target_lang, api_key)
        if translated_message:
            display_message = "{}{}".format(w.color("cyan"), translated_message)
            w.prnt(w.current_buffer(), display_message)
            return "{} {} :{}".format(command, channel, translated_message)

    return string


def translate_command_cb(data, buffer, args):
    argv = args.split(" ")
    command = argv[0] if len(argv) > 0 else ""

    if command == "list":
        translate_channels_in = json.loads(w.config_get_plugin("translate_channels_in"))
        translate_channels_out = json.loads(w.config_get_plugin("translate_channels_out"))
        w.prnt(buffer, "Channels for incoming translation:")
        for channel, lang in translate_channels_in.items():
            w.prnt(buffer, "  {} -> {}".format(channel, lang))
        w.prnt(buffer, "Channels for outgoing translation:")
        for channel, lang in translate_channels_out.items():
            w.prnt(buffer, "  {} -> {}".format(channel, lang))
    elif command in ["addin", "addout"]:
        if len(argv) != 4:
            w.prnt(buffer, "Usage: /translate addin|addout <server> <channel> <target_lang>")
            return w.WEECHAT_RC_ERROR
        server_channel = get_full_channel_name(argv[2], argv[1])
        target_lang = argv[3]
        translate_channels = json.loads(w.config_get_plugin("translate_channels_in" if command == "addin" else "translate_channels_out"))
        translate_channels[server_channel] = target_lang
        w.config_set_plugin("translate_channels_in" if command == "addin" else "translate_channels_out", json.dumps(translate_channels))
        w.prnt(buffer, "{} added for {} translation to {}.".format(server_channel, "incoming" if command == "addin" else "outgoing", target_lang))
    elif command in ["delin", "delout"]:
        if len(argv) != 3:
            w.prnt(buffer, "Usage: /translate delin|delout <server> <channel>")
            return w.WEECHAT_RC_ERROR
        server_channel = get_full_channel_name(argv[2], argv[1])
        translate_channels = json.loads(w.config_get_plugin("translate_channels_in" if command == "delin" else "translate_channels_out"))
        if server_channel in translate_channels:
            del translate_channels[server_channel]
            w.config_set_plugin("translate_channels_in" if command == "delin" else "translate_channels_out", json.dumps(translate_channels))
            w.prnt(buffer, "{} removed from {} translation.".format(server_channel, "incoming" if command == "delin" else "outgoing"))
        else:
            w.prnt(buffer, "{} not found in {} translation settings.".format(server_channel, "incoming" if command == "delin" else "outgoing"))

    elif command == "code":
        magenta = w.color("magenta")
        reset = w.color("reset")
        codes = [
            ("Azerbaijani", "az"), ("Hausa", "ha"), ("Malay", "ms"), ("Spanish", "es"),
            ("Bambara", "bm"), ("Hawaiian", "haw"), ("Malayalam", "ml"), ("Sundanese", "su"),
            ("Basque", "eu"), ("Hebrew", "he"), ("Maltese", "mt"), ("Swahili", "sw"),
            ("Belarusian", "be"), ("Hindi", "hi"), ("Maori", "mi"), ("Swedish", "sv"),
            ("Bengali", "bn"), ("Hmong", "hmn"), ("Marathi", "mr"), ("Tagalog", "tl"),
            ("Bhojpuri", "bho"), ("Hungarian", "hu"), ("Meiteilon", "mni"), ("Tajik", "tg"),
            ("Bosnian", "bs"), ("Icelandic", "is"), ("Mizo (lus)", "lus"), ("Tamil", "ta"),
            ("Bulgarian", "bg"), ("Igbo", "ig"), ("Mongolian", "mn"), ("Tatar", "tt"),
            ("Catalan", "ca"), ("Ilocano (ilo)", "ilo"), ("Myanmar (my)", "my"), ("Telugu", "te"),
            ("Cebuano", "ceb"), ("Indonesian", "id"), ("Nepali", "ne"), ("Thai", "th"),
            ("Chinese (Simpl)", "zh-CN"), ("Irish", "ga"), ("Norwegian", "no"), ("Tigrinya", "ti"),
            ("Chinese (Trad)", "zh-TW"), ("Italian", "it"), ("Nyanja (ny)", "ny"), ("Tsonga", "ts"),
            ("Corsican", "co"), ("Japanese", "ja"), ("Odia (or)", "or"), ("Turkish", "tr"),
            ("Croatian", "hr"), ("Javanese", "jv"), ("Oromo (om)", "om"), ("Turkmen", "tk"),
            ("Czech", "cs"), ("Kannada", "kn"), ("Pashto", "ps"), ("Twi (ak)", "ak"),
            ("Danish", "da"), ("Kazakh", "kk"), ("Persian", "fa"), ("Ukrainian", "uk"),
            ("Dhivehi", "dv"), ("Khmer", "km"), ("Polish", "pl"), ("Urdu", "ur"),
            ("Dogri (doi)", "doi"), ("Kinyarwanda", "rw"), ("Portuguese", "pt"), ("Uyghur", "ug"),
            ("Dutch", "nl"), ("Konkani (gom)", "gom"), ("Punjabi", "pa"), ("Uzbek", "uz"),
            ("English", "en"), ("Korean", "ko"), ("Quechua", "qu"), ("Vietnamese", "vi"),
            ("Esperanto", "eo"), ("Krio (kri)", "kri"), ("Romanian", "ro"), ("Welsh", "cy"),
            ("Estonian", "et"), ("Kurdish", "ku"), ("Russian", "ru"), ("Xhosa", "xh"),
            ("Ewe", "ee"), ("Kurdish (ckb)", "ckb"), ("Samoan", "sm"), ("Yiddish", "yi"),
            ("Filipino", "fil"), ("Kyrgyz", "ky"), ("Sanskrit", "sa"), ("Yoruba", "yo"),
            ("Finnish", "fi"), ("Lao", "lo"), ("Scots (gd)", "gd"), ("Zulu", "zu"),
            ("French", "fr"), ("Latin", "la"), ("Sepedi (nso)", "nso"),
            ("Frisian", "fy"), ("Latvian", "lv"), ("Serbian", "sr"),
        ]
        w.prnt("", "Available language codes:")
        column_width = 20
        for i in range(0, len(codes), 4):
            line = "".join(f"{name.ljust(column_width - len(code))}{magenta}{code}{reset}    " for name, code in codes[i:i+4])
            w.prnt(buffer, line)

    elif command == "help":
        w.prnt(buffer, "/translate command usage:")
        w.prnt(buffer, "/translate list - Show all channels with translation settings")
        w.prnt(buffer, "/translate addin <server> <channel> <target_lang> - Add a channel to translate incoming messages")
        w.prnt(buffer, "/translate addout <server> <channel> <target_lang> - Add a channel to translate outgoing messages")
        w.prnt(buffer, "/translate delin <server> <channel> - Remove a channel from translating incoming messages")
        w.prnt(buffer, "/translate delout <server> <channel> - Remove a channel from translating outgoing messages")
        w.prnt(buffer, "/translate code - Show available language codes for translation")
        w.prnt(buffer, "/translate help - Show this help message")

    else:
        w.prnt(buffer, "Unknown command. Use /translate help for usage information.")

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_modifier("irc_in_privmsg", "translate_incoming_message_cb", "")
    w.hook_modifier("irc_out_privmsg", "translate_outgoing_message_cb", "")
    w.hook_command("translate", "Manage translation settings",
                   "list | addin <server> <channel> <target_lang> | addout <server> <channel> <target_lang> | delin <server> <channel> | delout <server> <channel> | code | help",
                   "list: show all channels with translation settings\n"
                   "addin: add a channel to translate incoming messages\n"
                   "addout: add a channel to translate outgoing messages\n"
                   "delin: remove a channel from translating incoming messages\n"
                   "delout: remove a channel from translating outgoing messages\n"
                   "code: show available language codes for translation\n"
                   "help: show help information for the /translate command\n",
                   "list || addin %(irc_servers) %(irc_channels) || addout %(irc_servers) %(irc_channels) || delin %(irc_servers) %(irc_channels) || delout %(irc_servers) %(irc_channels) || code || help",
                   "translate_command_cb", "")
