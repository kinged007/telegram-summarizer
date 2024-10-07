# Telegram Message Summarizer

This script connects to sepecific channels/groups, collects the last messages from a predefined number of days, then compiles them into a LLM request. The response can then be sent to a designated channel.

This script signs into a users account. It has not been tested with a Bot account, but should work in theory.

To get the channel ID's, you can forward any message from the channel you want to work with, to an ID Bot (eg. @username_to_id_bot). The ID should start with -100 for groups or channels.

## Usage

Rename the `sample.env` file to `.env` and modify the variables.

Run `sh run.sh` or `run.bat` to start the script.