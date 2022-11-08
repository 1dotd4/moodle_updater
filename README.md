1. Create a toml config

```
```

2. Install python requirements and test

```
pip install -r requirements.txt
./moodle_updater.sh -c your_conf.toml
```

3. Add to crontab
```
crontab -e

0      *       *       *       *       cd ~/your_working_directory && ./moodle_updater.py -c your_conf.toml
```
