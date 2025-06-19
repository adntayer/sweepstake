def print_colored(text, color):
    colors = {
        # Regular Foreground Colors
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
        # Extra 256-color Foreground Colors
        "orange": "\033[38;5;208m",
        "pink": "\033[38;5;213m",
        "violet": "\033[38;5;177m",
        "teal": "\033[38;5;30m",
        "lime": "\033[38;5;118m",
        "sky_blue": "\033[38;5;117m",
        "gold": "\033[38;5;220m",
        "peach": "\033[38;5;216m",
        "turquoise": "\033[38;5;80m",
        "salmon": "\033[38;5;209m",
        "rose": "\033[38;5;205m",
        "grape": "\033[38;5;99m",
        "mint": "\033[38;5;121m",
        "navy": "\033[38;5;19m",
        "lavender": "\033[38;5;183m",
        "coral": "\033[38;5;203m",
        "aqua": "\033[38;5;45m",
        "cherry": "\033[38;5;161m",
        "steel": "\033[38;5;67m",
        "tan": "\033[38;5;180m",
        "indigo": "\033[38;5;54m",
        "plum": "\033[38;5;134m",
        "moss": "\033[38;5;100m",
        "sand": "\033[38;5;187m",
        "ice": "\033[38;5;153m",
        # Styles
        "bold": "\033[1m",
        "underline": "\033[4m",
        "reverse": "\033[7m",
    }

    reset_color = "\033[0m"

    if color in colors:
        print(f"{colors[color]}{text}{reset_color}")
    else:
        print(text)
