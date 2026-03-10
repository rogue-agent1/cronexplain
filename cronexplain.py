#!/usr/bin/env python3
"""cronexplain - Parse and explain cron expressions in plain English.

One file. Zero deps. Understands cron.

Usage:
  cronexplain.py "*/5 * * * *"        → Every 5 minutes
  cronexplain.py "0 9 * * 1-5"        → At 09:00, Monday through Friday
  cronexplain.py "0 0 1 * *"          → At midnight on the 1st of every month
  cronexplain.py next "*/15 * * * *"   → Show next 5 occurrences
"""

import argparse
import sys
import time
import calendar
from datetime import datetime, timedelta


MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}
MONTH_ABBR = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def parse_field(field: str, lo: int, hi: int, names: dict = None) -> set[int]:
    """Parse a cron field into a set of values."""
    if names:
        for name, val in names.items():
            field = field.lower().replace(name, str(val))

    values = set()
    for part in field.split(','):
        step = 1
        if '/' in part:
            part, step_s = part.split('/', 1)
            step = int(step_s)

        if part == '*':
            values.update(range(lo, hi + 1, step))
        elif '-' in part:
            a, b = part.split('-', 1)
            values.update(range(int(a), int(b) + 1, step))
        else:
            values.add(int(part))

    return values


def parse_cron(expr: str) -> tuple[set, set, set, set, set]:
    """Parse 5-field cron expression."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 fields, got {len(parts)}: {expr}")

    minutes = parse_field(parts[0], 0, 59)
    hours = parse_field(parts[1], 0, 23)
    days = parse_field(parts[2], 1, 31)
    months = parse_field(parts[3], 1, 12, MONTH_ABBR)
    weekdays = parse_field(parts[4], 0, 6, DAY_ABBR)

    return minutes, hours, days, months, weekdays


def explain_field(field: str, lo: int, hi: int, names: dict = None) -> str:
    """Explain a single cron field in English."""
    if field == '*':
        return "every"
    if '/' in field and field.startswith('*/'):
        step = field.split('/')[1]
        return f"every {step}"
    if '/' in field:
        base, step = field.split('/', 1)
        return f"every {step} starting at {base}"
    if '-' in field and ',' not in field:
        a, b = field.split('-', 1)
        return f"{a} through {b}"
    return field


def explain(expr: str) -> str:
    """Generate human-readable explanation."""
    parts = expr.strip().split()
    if len(parts) != 5:
        return f"Invalid: expected 5 fields, got {len(parts)}"

    m, h, dom, mon, dow = parts
    pieces = []

    # Time
    if m == '*' and h == '*':
        pieces.append("Every minute")
    elif m.startswith('*/'):
        pieces.append(f"Every {m.split('/')[1]} minutes")
    elif h == '*':
        pieces.append(f"At minute {m} of every hour")
    elif m.startswith('*/') and h != '*':
        pieces.append(f"Every {m.split('/')[1]} minutes during hour(s) {h}")
    else:
        # Specific time(s)
        hours_vals = parse_field(h, 0, 23)
        min_vals = parse_field(m, 0, 59)
        if len(hours_vals) <= 3 and len(min_vals) <= 3:
            times = []
            for hv in sorted(hours_vals):
                for mv in sorted(min_vals):
                    times.append(f"{hv:02d}:{mv:02d}")
            pieces.append(f"At {', '.join(times)}")
        else:
            pieces.append(f"At minute {m}, hour {h}")

    # Day of month
    if dom != '*':
        if '-' in dom:
            pieces.append(f"on days {dom}")
        elif ',' in dom:
            pieces.append(f"on days {dom}")
        elif dom.startswith('*/'):
            pieces.append(f"every {dom.split('/')[1]} days")
        else:
            day_int = int(dom)
            suffix = {1: 'st', 2: 'nd', 3: 'rd', 21: 'st', 22: 'nd', 23: 'rd', 31: 'st'}.get(day_int, 'th')
            pieces.append(f"on the {day_int}{suffix}")

    # Month
    if mon != '*':
        month_vals = parse_field(mon, 1, 12, MONTH_ABBR)
        month_names = [MONTHS[v] for v in sorted(month_vals) if 1 <= v <= 12]
        if len(month_names) <= 4:
            pieces.append(f"in {', '.join(month_names)}")
        else:
            pieces.append(f"in months {mon}")

    # Day of week
    if dow != '*':
        dow_vals = parse_field(dow, 0, 6, DAY_ABBR)
        # Map: 0=Sun, 1=Mon ... 6=Sat
        day_map = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_names = [day_map[v] for v in sorted(dow_vals) if 0 <= v <= 6]
        if dow == '1-5':
            pieces.append("Monday through Friday")
        elif dow == '0,6' or dow == '6,0':
            pieces.append("on weekends")
        elif len(day_names) <= 4:
            pieces.append(f"on {', '.join(day_names)}")
        else:
            pieces.append(f"on days of week {dow}")

    return ', '.join(pieces)


def next_occurrences(expr: str, count: int = 5, start: datetime = None) -> list[datetime]:
    """Calculate next N occurrences of a cron expression."""
    minutes, hours, days, months, weekdays = parse_cron(expr)

    if start is None:
        start = datetime.now()
    # Start from next minute
    current = start.replace(second=0, microsecond=0) + timedelta(minutes=1)

    results = []
    max_iter = 525600  # 1 year of minutes

    for _ in range(max_iter):
        if (current.minute in minutes and
            current.hour in hours and
            current.day in days and
            current.month in months and
            current.weekday() in {(d - 1) % 7 for d in weekdays}
                if weekdays != {0, 1, 2, 3, 4, 5, 6}
                else True):
            # Check weekday: cron 0=Sun, Python 0=Mon
            dow_python = current.weekday()  # 0=Mon
            dow_cron = (dow_python + 1) % 7  # 0=Sun
            if dow_cron in weekdays:
                results.append(current)
                if len(results) >= count:
                    break
        current += timedelta(minutes=1)

    return results


def main():
    parser = argparse.ArgumentParser(description="Explain cron expressions")
    parser.add_argument("command", nargs="?", default="explain", help="explain (default) or next")
    parser.add_argument("expr", help="Cron expression (5 fields, quoted)")
    parser.add_argument("-n", "--count", type=int, default=5, help="Number of occurrences for 'next'")

    args = parser.parse_args()

    # Handle "next" as first arg
    if args.command == "next":
        expr = args.expr
    elif args.command == "explain":
        expr = args.expr
    else:
        # command is actually the expr, expr might be part of it
        expr = args.command
        if args.expr and args.expr != "explain":
            expr = f"{args.command} {args.expr}"

    try:
        desc = explain(expr)
        print(f"  {expr}")
        print(f"  → {desc}")

        if args.command == "next":
            print()
            for dt in next_occurrences(expr, args.count):
                print(f"  {dt.strftime('%Y-%m-%d %H:%M (%A)')}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
