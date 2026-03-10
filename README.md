# cronexplain

Parse and explain cron expressions in plain English.

One file. Zero deps. Understands cron.

## Usage

```bash
python3 cronexplain.py "*/5 * * * *"
# → Every 5 minutes

python3 cronexplain.py "0 9 * * 1-5"
# → At 09:00, Monday through Friday

python3 cronexplain.py "0 0 1 * *"
# → At 00:00, on the 1st

# Show next occurrences
python3 cronexplain.py next "*/15 * * * *" -n 10
```

## Requirements

Python 3.8+. No dependencies.

## License

MIT
