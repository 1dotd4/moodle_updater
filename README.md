## Rationale
[Moodle](https://moodle.org) is a platform we use at university. It is almost like a forum, but you will not see when the professor updates stuff, for example new assignments, new slides.
So this simple script was assembled to list the available material. The list is cached, and if a change is found, a notification is sent in a Telegram channel with the changes.

## Install

1. Create a toml config with appopriate tokens, keys and passwords

```
save_file = "last_list_update"
root_url = "https://your_moodle_url.org/"
course_id = "12345"
guest_pass = "fun"
telegram_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
telegram_channel = "-1234567890123"
```

2. Install python requirements and test it manually

```
pip install -r requirements.txt
./moodle_updater.sh -c your_conf.toml
```

3. Add to crontab with `crontab -e`
```
0      *       *       *       *       cd ~/your_working_directory && ./moodle_updater.py -c your_conf.toml
```
