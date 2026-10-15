from src.config import parse_args


def test_parse_chats_single():
    args = parse_args(["--chats", "John", "--mock"])
    assert args.chats == ["John"]
    assert args.mock is True


def test_parse_chats_comma_separated():
    args = parse_args(["--chats", "John,Alice", "--mock"])
    # parse_args keeps comma string as one entry; telegram_utils splits it
    assert args.chats == ["John,Alice"]


def test_parse_job():
    args = parse_args(["--job", "DailyUpdate"])
    assert args.job == ["DailyUpdate"]


def test_parse_days_default():
    args = parse_args(["--chats", "John", "--mock"])
    assert args.days == 3


def test_parse_debug_flag():
    args = parse_args(["--chats", "John", "--debug"])
    assert args.debug is True


def test_parse_prompt_template():
    args = parse_args(["--chats", "John", "--prompt_template", "Technical"])
    assert args.prompt_template == ["Technical"]
