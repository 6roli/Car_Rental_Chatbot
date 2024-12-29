def print_colored(text, color="default"):
    COLORS = {
        "default": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
    }
    color_code = COLORS.get(color.lower(), COLORS["default"])
    print(f"{color_code}{text}\033[0m")