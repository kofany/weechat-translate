                display_translated_message(message_id, translated_text, message_info['server'], message_info['channel'], message_info['nick'])
            else:
                debug_print("", "[Translate Debug] Message ID not found in translated_texts after translation.")
        else:
            debug_print(buffer, "[Translate Debug] Error in translation response: No translations found")

    return w.WEECHAT_RC_OK

def translate(buffer, source_lang, target_lang, api_key, callback_action, message_id, text_to_translate):
    post_data = json.dumps({'q': text_to_translate, 'source': source_lang, 'target': target_lang, 'format': 'text'})
    headers = "Content-Type: application/json\nx-goog-api-key: " + api_key
    options = {"postfields": post_data, "httpheader": headers}
    callback_data = json.dumps({
        'buffer': buffer,
        'action': callback_action,
        'api_key': api_key,
        'target_lang': target_lang,
        'message_id': message_id
    })

    w.hook_url(TRANSLATE_API_URL, options, 20000, "api_request_cb", callback_data)
    debug_print("", "[Translate Debug] Hook URL called for translation.")
    debug_print("", f"[Translate Debug translate END] Current translated_texts content: {translated_texts}")


def translate_incoming_message_cb(data, modifier, modifier_data, string):
    api_key = w.config_get_plugin("api_key")
    if not api_key:
        debug_print("", "[Translate Debug] API key is not set.")
        return string

    parsed_data = w.info_get_hashtable("irc_message_parse", {"message": string})
    channel = parsed_data["channel"]
    message = parsed_data["text"]
    server = modifier_data
    nick = parsed_data["nick"]
    message_id = str(hash(message))

    full_channel_name = get_full_channel_name(channel, server)
    translate_channels_in = json.loads(w.config_get_plugin("translate_channels_in"))

    if full_channel_name in translate_channels_in:
        target_lang = translate_channels_in[full_channel_name]
        translated_texts[message_id] = {
            "raw_message": string,  # Przechowujemy surowy tekst wiadomości
            "message": message,  # Przechowujemy przetłumaczony tekst wiadomości
            "channel": channel,
            "server": server,
            "nick": nick,  # Przechowujemy nadawcę wiadomości
        }
        detect_language_and_translate("", message_id, message, server, channel, target_lang, api_key)
        return ""
    else:
        return string

def deb_print(message):
    w.prnt("", "DEBUG: " + message)

def get_full_chan_name(channel, server):
    full_channel_name = "{}@{}".format(channel, server)
    return full_channel_name

def get_full_identifier(name, server):
    if name.startswith("#"):
        full_identifier = "{}@{}".format(name, server)
    else:
        full_identifier = "{}@{}".format(name, server)
    return full_identifier


def input_return_cb(data, buffer, command):
    input_text = w.buffer_get_string(buffer, "input")
    if input_text.startswith("/"):
        return w.WEECHAT_RC_OK


    server = w.buffer_get_string(buffer, "localvar_server")
    buffer_type = w.buffer_get_string(buffer, "localvar_type")
    nick = w.buffer_get_string(buffer, "localvar_nick")  # Przeniesienie definicji zmiennej nick na początek funkcji

    if buffer_type == "channel":
        target = w.buffer_get_string(buffer, "localvar_channel")
    else:
        target = w.buffer_get_string(buffer, "localvar_name").split('.')[1]  # Dla prywatnych wiadomości użyj części po kropce

    if input_text.startswith("@"):
        _, lang_code_and_text = input_text.split('@', 1)
        lang_code, text_to_translate = lang_code_and_text.split(' ', 1)
        translate_out(buffer, text_to_translate, lang_code, settings["api_key"], nick)
        w.buffer_set(buffer, "input", "")  # Clears the input field
    else:
        full_identifier = f"{target}@{server}" if buffer_type == "private" else get_full_chan_name(target, server)
        translate_channels_out = json.loads(w.config_get_plugin("translate_channels_out"))
        if full_identifier in translate_channels_out:
            target_lang = translate_channels_out[full_identifier]
            translate_out(buffer, input_text, target_lang, settings["api_key"], nick)
            w.buffer_set(buffer, "input", "")  # Clears the input field
        else:
            return w.WEECHAT_RC_OK

    return w.WEECHAT_RC_OK

def api_out_request_cb(data, url, request, response):
    buffer, original_text, lang_code, nick = data.split(';', 3)
    try:
        response_data = json.loads(response['output'])  # Zakładam, że odpowiedź jest w 'output'
        if 'data' in response_data and 'translations' in response_data['data']:
            translated_text = response_data['data']['translations'][0]['translatedText']
            server = w.buffer_get_string(buffer, "localvar_server")
            channel = w.buffer_get_string(buffer, "localvar_channel")

            channel_buffer = w.info_get("irc_buffer", "{},{}".format(server, channel))
            if channel_buffer:
                display_message = "{}{}{}\t{}".format(w.color("cyan"), "original", w.color("reset"), original_text)
                w.prnt(w.current_buffer(), display_message)
                w.command(channel_buffer, "/msg {} {}".format(channel, translated_text))
        else:
            deb_print("Error in translation response: No translations found")
    except Exception as e:
        deb_print("Error in api_out_request_cb: " + str(e))

    return w.WEECHAT_RC_OK

def translate_out(buffer, text, lang_code, api_key, nick):
    post_data = json.dumps({'q': text, 'target': lang_code, 'format': 'text'})
    headers = "Content-Type: application/json\nx-goog-api-key: " + api_key
    options = {"postfields": post_data, "httpheader": headers}
    callback_data = ';'.join([buffer, text, lang_code, nick])
    w.hook_url(TRANSLATE_API_URL, options, 20000, "api_out_request_cb", callback_data)

def translate_command_cb(data, buffer, args):
    argv = args.split(" ")
    command = argv[0] if len(argv) > 0 else ""

    if command == "list":
        translate_channels_in = json.loads(w.config_get_plugin("translate_channels_in"))
        translate_channels_out = json.loads(w.config_get_plugin("translate_channels_out"))
        w.prnt(buffer, "Channels/nicks for incoming translation:")
        for channel, lang in translate_channels_in.items():
            w.prnt(buffer, "  {} -> {}".format(channel, lang))
        w.prnt(buffer, "Channels/nicks for outgoing translation:")
        for channel, lang in translate_channels_out.items():
            w.prnt(buffer, "  {} -> {}".format(channel, lang))
    elif command in ["addin", "addout"]:
        if len(argv) != 4:
            w.prnt(buffer, "Usage: /translate addin|addout <server> <channel/nick> <target_lang>")
            return w.WEECHAT_RC_ERROR
        server_channel = get_full_channel_name(argv[2], argv[1])
        target_lang = argv[3]
        translate_channels = json.loads(w.config_get_plugin("translate_channels_in" if command == "addin" else "translate_channels_out"))
        translate_channels[server_channel] = target_lang
        w.config_set_plugin("translate_channels_in" if command == "addin" else "translate_channels_out", json.dumps(translate_channels))
        w.prnt(buffer, "{} added for {} translation to {}.".format(server_channel, "incoming" if command == "addin" else "outgoing", target_lang))
    elif command in ["delin", "delout"]:
        if len(argv) != 3:
            w.prnt(buffer, "Usage: /translate delin|delout <server> <channel/nick>")
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
        w.prnt(buffer, "/translate addin <server> <channel/nick> <target_lang> - Add a channel to translate incoming messages")
        w.prnt(buffer, "/translate addout <server> <channel/nick> <target_lang> - Add a channel to translate outgoing messages")
        w.prnt(buffer, "/translate delin <server> <channel/nick> - Remove a channel from translating incoming messages")
        w.prnt(buffer, "/translate delout <server> <channel/nick> - Remove a channel from translating outgoing messages")
        w.prnt(buffer, "/translate code - Show available language codes for translation")
        w.prnt(buffer, "/translate help - Show this help message")

    else:
        w.prnt(buffer, "Unknown command. Use /translate help for usage information.")

    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    w.hook_command_run("/input return", "input_return_cb", "")
    w.hook_modifier("irc_in_privmsg", "translate_incoming_message_cb", "")
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




