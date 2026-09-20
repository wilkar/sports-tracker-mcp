MS_TO_KMH = 3.6
MS_TO_MPH = 2.23693629
KM_TO_MILES = 0.621371192


def format_distance(meters: float, imperial: bool = False) -> tuple[float, str]:
    val = (meters / 1000.0) * (KM_TO_MILES if imperial else 1.0)
    unit = "mi" if imperial else "km"
    return round(val, 2), f"{val:,.2f} {unit}"


def format_speed(meters_per_sec: float, imperial: bool = False) -> str:
    multiplier = MS_TO_MPH if imperial else MS_TO_KMH
    unit = "mph" if imperial else "km/h"
    speed = round(meters_per_sec * multiplier, 1)
    return f"{speed:.1f} {unit}"


def format_pace(meters_per_sec: float, imperial: bool = False) -> str:
    if meters_per_sec <= 0:
        return "00:00"
    speed = meters_per_sec * (MS_TO_MPH if imperial else MS_TO_KMH)
    pace = 60.0 / speed
    minutes = int(pace)
    seconds = int(60.0 * (pace - minutes))
    return f"{minutes}:{seconds:02d}"


def format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
