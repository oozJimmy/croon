"""
croon - a terminal lunar/solar info display
      - Gets data from US Navy Astronomical Applications Department Data Services via web API

      JDK ({:()
"""

import datetime
from shutil import get_terminal_size
import sys
import json
import requests
from rich import inspect, print as rprint
from rich.markup import escape
from rich.layout import Layout
from rich.console import Console
from rich.theme import Theme


def main():
    args: list[str] = sys.argv
    if "--help" in sys.argv or "help" in sys.argv:
        print_usage_msg()
        exit(0)

    lat, long = get_coord_args(args)
    time_zone = -5  # EST, bitch

    # get terminal dimensions, default to 80 col, 20 rows
    (term_width, term_height) = get_terminal_size((80, 20))
    curr_date = datetime.date.today()

    # web request to US Navy Astronomical Applications Department
    oneday_resp_json = send_request_moonsun_oneday(lat, long, curr_date, time_zone)
    phase_resp_data = send_request_moonphases(curr_date)

    oneday_data = oneday_resp_json["properties"]["data"]

    phase_data = phase_resp_data["phasedata"]

    data = {}
    data = format_moon_data(oneday_data, phase_data)

    style = "[bold medium_purple]"
    end_style = "[/]"
    text_to_display = "\n".join(
        (
            f"{style}Date:{end_style} {data['day_of_week']} {curr_date.month}/{curr_date.day}/{curr_date.year}",
            f"{style}Coordinates: {end_style}{lat}, {long}",
            f"{style}Current Phase:{end_style} {data['current_phase']}",
            f"{style}Fracillum:{end_style} {data['fracillum']}",
            f"{style}Next Phase: {end_style}{data['next_phase']['phase']} {data['next_phase']['month']}/{data['next_phase']['day']}/{data['next_phase']['year']} {data['next_phase']['time']}",
            f"{style}Moonrise:{end_style} {data['moonrise']}",
            f"{style}Moonset:{end_style} {data['moonset']}",
            f"{style}Sunrise:{end_style} {data['sunrise']}",
            f"{style}Sunset:{end_style} {data['sunset']}",
            f"{style}Dawn:{end_style} {data['dawn']}",
            f"{style}Dusk:{end_style} {data['dusk']}",
        )
    )

    moon_phases: list[str] = get_moon_phases_art()

    print_rich_console(
        moon_phases[phase_to_index(oneday_data["curphase"])],
        text_to_display,
        term_width,
        14,
    )


def get_coord_args(args) -> (float, float):
    # croon -c -67.62,75.05
    # croon -c [latitude],[longitude]

    if "-c" not in args:
        return 42.1, -75.9  # default coordinates

    (lat, long) = args[args.index("-c") + 1].split(",")

    try:
        lat = float(lat)
        long = float(long)
    except Exception:
        rprint("[red]Invalid args: bad float number format")
        exit(1)

    lat, long = wrap_coords(lat, long)

    return lat, long


def wrap_coords(lat, long) -> (float, float):
    # fix latitude to range -90, 90
    if lat > 90.0:
        lat %= -90.0
    elif lat < -90.0:
        lat %= 90.0

    # fx longitude to range -180, 180
    if long > 180.0:
        long %= -180.0
    elif long < -180.0:
        long %= 180.0

    return lat, long


def print_usage_msg():
    rprint("[bold medium_purple3]croon[/] - a terminal lunar/solar information display")
    rprint(f"[bold blue]Usage: [/][blue]croon -c {escape('[[latitude],[longitude]]')}")


def get_moon_phases_art() -> list[str]:
    with open("phases.txt", "r") as art_file:
        file_str = art_file.read()
        phases = file_str.split("\n\n\n")
        if len(phases) != 8:
            rprint("[red]Error loading ascii art, did not find eight pieces[/red]")
            exit(1)
        return phases


def phase_to_index(phase: str) -> int:
    # Takes a phase string and returns an index for which ascii moon art to show
    index: int = 0

    phase_choices = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]

    if phase in phase_choices:
        index = phase_choices.index(phase)
    else:
        rprint("[red]Error: phase_to_index, Moon phase art could not be selected[/]")
    return index


def send_request_moonsun_oneday(lat, long, date, time_zone) -> dict:
    # Requests lunar/solar data and returns json
    # Connects to the one day lunar and solar Navy API endpoint
    params: dict = {
        "coords": f"{lat},{long}",
        "date": f"{date.year}-{date.month}-{date.day}",
        "tz": f"-5",
    }
    # resp = requests.get("https://aa.usno.navy.mil/api/rstt/oneday", params)
    resp = requests.get(
        f"https://aa.usno.navy.mil/api/rstt/oneday?coords={lat},{long}&date={date.year}-{date.month}-{date.day}&tz={time_zone}"
    )
    if resp.status_code != 200:
        rprint("[red] Invalid non-200 api response (moon and sun one day)[/]")
        exit(1)

    return json.loads(resp.text)


def send_request_moonphases(date):
    # Requests lunar phases data and returns json
    # Connects to the phases of the moon Navy API endpoint
    num_phases = 2
    params = {
        "nump": num_phases,
        "date": f"{date.year}-{date.month}-{date.day}",
    }
    resp = requests.get("https://aa.usno.navy.mil/api/moon/phases/date", params)
    if not resp.status_code == 200:
        rprint("[red]Invalid non-200 api response (phases)[/]")
        exit(1)

    return json.loads(resp.text)


def print_rich_console(
    moon_art: str, text_to_display: str, term_width: int, term_height: int
):
    console = Console(height=term_height, theme=Theme(inherit=False))

    layout: Layout = Layout(size=10)
    layout.split_row(
        Layout(f"\n{moon_art}", name="left"),
        Layout(text_to_display, name="right"),
    )
    layout["left"].size = 30
    layout["right"].size = term_width - 30
    console.print(layout)


def format_moon_data(oneday: dict, phases: dict) -> dict:
    try:
        moon_transit = oneday["moondata"]
        sun_transit = oneday["sundata"]

        for item in sun_transit:
            if item["phen"] == "Set":
                sunset_time = item["time"]
            elif item["phen"] == "Rise":
                sunrise_time = item["time"]
            elif item["phen"] == "Begin Civil Twilight":
                dawn = item["time"]
            elif item["phen"] == "End Civil Twilight":
                dusk = item["time"]

        for item in moon_transit:
            if item["phen"] == "Set":
                moonset_time = item["time"]
            elif item["phen"] == "Rise":
                moonrise_time = item["time"]

        out_data = {
            "day_of_week": oneday["day_of_week"],
            "current_phase": oneday["curphase"],
            "fracillum": oneday["fracillum"],
            "sunrise": sunrise_time,
            "sunset": sunset_time,
            "moonrise": moonrise_time,
            "moonset": moonset_time,
            "dawn": dawn,
            "dusk": dusk,
            "next_phase": phases[0],
        }

    except KeyError:
        print("Error formatting data")
        print(KeyError)
        exit(1)

    return out_data


if __name__ == "__main__":
    main()
