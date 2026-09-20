from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .constants import ACTIVITY_MAPPING
from .formatting import (
    format_distance,
    format_duration,
    format_pace,
    format_speed,
)


def _dt_from_ms(ms: Any) -> datetime | None:
    """Convert epoch milliseconds to a UTC datetime, or None if invalid/missing."""
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _opt_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _opt_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ============================================================================
# 1. Workout Summaries & Details
# ============================================================================


class WorkoutSummary(BaseModel):
    workout_key: str = Field(description="Unique workout identifier")
    sport: str = Field(description="Sport name, e.g. running, cycling, walking")
    start_time: str = Field(description="ISO 8601 formatted start time")
    duration_formatted: str = Field(description="Duration in HH:MM:SS format")
    distance_formatted: str = Field(description="Distance with unit, e.g. '5.20 km'")
    avg_speed_formatted: str = Field(description="Speed with unit, e.g. '10.5 km/h'")
    avg_pace_formatted: str = Field(description="Pace in MM:SS min/km format")
    distance_km: float = Field(description="Distance in kilometers")
    duration_seconds: float = Field(description="Active duration in seconds")
    calories_kcal: int | None = Field(
        default=None, description="Calories burned in kcal"
    )
    avg_hr: int | None = Field(default=None, description="Average heart rate in bpm")
    max_hr: int | None = Field(default=None, description="Maximum heart rate in bpm")
    step_count: int | None = Field(
        default=None, description="Total steps, if applicable"
    )

    @classmethod
    def from_api(
        cls, raw: dict[str, Any], imperial: bool = False
    ) -> "WorkoutSummary | None":
        """Converts raw Sports Tracker API dictionary to WorkoutSummary, returning None if malformed."""
        workout_key = raw.get("workoutKey") or raw.get("key")
        start_dt = _dt_from_ms(raw.get("startTime"))
        if not workout_key or not start_dt:
            return None

        dist_m = _safe_float(raw.get("totalDistance"), 0.0)
        time_s = _safe_float(raw.get("totalTime"), 0.0)
        speed_ms = _safe_float(raw.get("avgSpeed"), 0.0)
        dist_val, dist_str = format_distance(dist_m, imperial=imperial)
        speed_str = format_speed(speed_ms, imperial=imperial)
        pace_str = format_pace(speed_ms, imperial=imperial)

        hr_data = raw.get("hrdata")
        hr_dict = hr_data if isinstance(hr_data, dict) else {}
        avg_hr_val = _opt_int(hr_dict.get("avg"))
        max_hr_val = _opt_int(hr_dict.get("hrmax") or hr_dict.get("max"))
        avg_hr = avg_hr_val if avg_hr_val and avg_hr_val > 0 else None
        max_hr = max_hr_val if max_hr_val and max_hr_val > 0 else None

        raw_step = _opt_int(raw.get("stepCount"))
        step_count = raw_step if raw_step and raw_step > 0 else None

        return cls(
            workout_key=str(workout_key),
            sport=ACTIVITY_MAPPING.get(raw.get("activityId", -1), "other"),
            start_time=start_dt.isoformat(),
            duration_formatted=format_duration(time_s),
            distance_formatted=dist_str,
            avg_speed_formatted=speed_str,
            avg_pace_formatted=pace_str,
            distance_km=dist_val,
            duration_seconds=round(time_s, 1),
            calories_kcal=_opt_int(raw.get("energyConsumption")),
            avg_hr=avg_hr,
            max_hr=max_hr,
            step_count=step_count,
        )


class TimeSeriesPoint(BaseModel):
    seconds: int = Field(description="Elapsed seconds from workout start")
    value: float = Field(description="Metric value at this time point")


class WorkoutDetail(WorkoutSummary):
    description: str | None = Field(
        default=None, description="Workout description or notes"
    )
    max_speed_formatted: str = Field(description="Max speed formatted with unit")
    ascent_meters: float = Field(default=0.0, description="Total ascent in meters")
    descent_meters: float = Field(default=0.0, description="Total descent in meters")
    recovery_time_hours: float | None = Field(
        default=None, description="Workout recovery time in hours"
    )
    cumulative_recovery_hours: float | None = Field(
        default=None, description="Total cumulative recovery time in hours"
    )
    training_stress_score: float | None = Field(
        default=None, description="Training stress score (TSS)"
    )
    peak_training_effect: float | None = Field(
        default=None, description="Peak training effect (PTE 1.0 - 5.0)"
    )
    peak_epoc: float | None = Field(default=None, description="Peak EPOC in ml/kg")
    gear: str | None = Field(
        default=None, description="Device or gear used (e.g. Suunto watch)"
    )
    heart_rate_zones: dict[str, str] | None = Field(
        default=None, description="Formatted time spent in each HR zone"
    )
    time_series: dict[str, list[TimeSeriesPoint]] = Field(
        default_factory=dict,
        description="Downsampled time series streams (heart_rate, altitude, speed)",
    )

    @classmethod
    def from_api(
        cls, raw: dict[str, Any], imperial: bool = False
    ) -> "WorkoutDetail | None":
        base = WorkoutSummary.from_api(raw, imperial=imperial)
        if base is None:
            return None

        max_speed_ms = _safe_float(raw.get("maxSpeed"), 0.0)
        max_speed_str = format_speed(max_speed_ms, imperial=imperial)

        exts = {
            e.get("type"): e for e in raw.get("extensions") or [] if isinstance(e, dict)
        }
        summary_ext = exts.get("SummaryExtension", {})
        intensity_ext = exts.get("IntensityExtension", {})

        rec_sec = _opt_float(raw.get("recoveryTime") or summary_ext.get("recoveryTime"))
        rec_hours = round(rec_sec / 3600.0, 1) if rec_sec is not None else None

        cum_rec_sec = _opt_float(raw.get("cumulativeRecoveryTime"))
        cum_rec_hours = (
            round(cum_rec_sec / 3600.0, 1) if cum_rec_sec is not None else None
        )

        tss_data = raw.get("tss")
        tss_val = (
            _opt_float(tss_data.get("trainingStressScore"))
            if isinstance(tss_data, dict)
            else None
        )

        gear_data = summary_ext.get("gear")
        gear_name = (
            gear_data.get("displayName") or gear_data.get("name")
            if isinstance(gear_data, dict)
            else None
        )

        hr_zones: dict[str, str] | None = None
        zones_data = (
            intensity_ext.get("zones", {}).get("heartRate")
            if isinstance(intensity_ext, dict)
            and isinstance(intensity_ext.get("zones"), dict)
            else None
        )
        if isinstance(zones_data, dict):
            hr_zones = {}
            for zone_key in ["zone1", "zone2", "zone3", "zone4", "zone5"]:
                if zone_key in zones_data and isinstance(zones_data[zone_key], dict):
                    zone_secs = _safe_float(zones_data[zone_key].get("totalTime"), 0.0)
                    hr_zones[zone_key] = format_duration(zone_secs)

        ascent = _safe_float(raw.get("totalAscent") or summary_ext.get("ascent"), 0.0)
        descent = _safe_float(
            raw.get("totalDescent") or summary_ext.get("descent"), 0.0
        )

        start_ts = _safe_int(raw.get("startTime"), 0)
        time_series: dict[str, list[TimeSeriesPoint]] = {}

        def _downsample_stream(
            pts: list[Any], scale: float = 1.0, target: int = 60
        ) -> list[TimeSeriesPoint]:
            valid: list[tuple[int, float]] = []
            for p in pts:
                if isinstance(p, dict) and isinstance(p.get("value"), (int, float)):
                    ts = _safe_int(p.get("timestamp"), start_ts)
                    sec = (
                        max(0, int((ts - start_ts) / 1000))
                        if start_ts > 0
                        else len(valid)
                    )
                    valid.append((sec, round(float(p["value"]) * scale, 1)))
            if not valid:
                return []
            if len(valid) <= target:
                return [TimeSeriesPoint(seconds=s, value=v) for s, v in valid]
            step = len(valid) / target
            sampled = []
            for i in range(target):
                idx = min(int(i * step), len(valid) - 1)
                s, v = valid[idx]
                sampled.append(TimeSeriesPoint(seconds=s, value=v))
            if sampled and sampled[-1].seconds != valid[-1][0]:
                sampled[-1] = TimeSeriesPoint(seconds=valid[-1][0], value=valid[-1][1])
            return sampled

        hr_stream = exts.get("HeartrateStreamExtension", {}).get("points")
        if isinstance(hr_stream, list) and hr_stream:
            time_series["heart_rate"] = _downsample_stream(hr_stream, scale=1.0)

        alt_stream = exts.get("AltitudeStreamExtension", {}).get("points")
        if isinstance(alt_stream, list) and alt_stream:
            alt_scale = 3.28084 if imperial else 1.0
            time_series["altitude"] = _downsample_stream(alt_stream, scale=alt_scale)

        spd_stream = exts.get("SpeedStreamExtension", {}).get("points")
        if isinstance(spd_stream, list) and spd_stream:
            spd_scale = 2.23694 if imperial else 3.6
            time_series["speed"] = _downsample_stream(spd_stream, scale=spd_scale)

        return cls(
            **base.model_dump(),
            description=raw.get("description") or None,
            max_speed_formatted=max_speed_str,
            ascent_meters=ascent,
            descent_meters=descent,
            recovery_time_hours=rec_hours,
            cumulative_recovery_hours=cum_rec_hours,
            training_stress_score=round(tss_val, 1) if tss_val is not None else None,
            peak_training_effect=_opt_float(summary_ext.get("pte")),
            peak_epoc=_opt_float(summary_ext.get("peakEpoc")),
            gear=gear_name,
            heart_rate_zones=hr_zones,
            time_series=time_series,
        )


# ============================================================================
# 2. Social Feed
# ============================================================================


class SocialFeedItem(BaseModel):
    feed_type: str = Field(description="Type of feed item, e.g. WORKOUT or AMBASSADOR")
    username: str | None = Field(default=None, description="Username of athlete")
    athlete_name: str | None = Field(default=None, description="Full name of athlete")
    workout_key: str | None = Field(
        default=None, description="Workout key if item is a workout"
    )
    sport: str | None = Field(
        default=None, description="Sport name if item is a workout"
    )
    start_time: str | None = Field(default=None, description="ISO 8601 start time")
    distance_formatted: str | None = Field(
        default=None, description="Distance formatted with unit"
    )
    duration_formatted: str | None = Field(
        default=None, description="Duration formatted as HH:MM:SS"
    )
    avg_speed_formatted: str | None = Field(
        default=None, description="Average speed formatted with unit"
    )
    description: str | None = Field(
        default=None, description="Workout description or post content"
    )
    likes_count: int = Field(default=0, description="Number of likes / reactions")
    comments_count: int = Field(default=0, description="Number of comments")

    @classmethod
    def from_api(cls, raw: dict[str, Any], imperial: bool = False) -> "SocialFeedItem":
        feed_type = raw.get("feedType", "UNKNOWN")
        if feed_type != "WORKOUT":
            return cls(feed_type=feed_type)

        start_dt = _dt_from_ms(raw.get("startTime"))
        start_time_iso = start_dt.isoformat() if start_dt else None

        dist_m = _safe_float(raw.get("totalDistance"), 0.0)
        time_s = _safe_float(raw.get("totalTime"), 0.0)
        speed_ms = _safe_float(raw.get("avgSpeed"), 0.0)

        _, dist_str = format_distance(dist_m, imperial=imperial)
        speed_str = format_speed(speed_ms, imperial=imperial)

        return cls(
            feed_type="WORKOUT",
            username=raw.get("username"),
            athlete_name=raw.get("fullname") or raw.get("username"),
            workout_key=raw.get("workoutKey"),
            sport=ACTIVITY_MAPPING.get(raw.get("activityId", -1), "other"),
            start_time=start_time_iso,
            distance_formatted=dist_str if dist_m > 0 else None,
            duration_formatted=format_duration(time_s) if time_s > 0 else None,
            avg_speed_formatted=speed_str if speed_ms > 0 else None,
            description=raw.get("description") or None,
            likes_count=_safe_int(raw.get("reactionCount"), 0),
            comments_count=_safe_int(raw.get("commentCount"), 0),
        )


# ============================================================================
# 3. User & Lifetime Stats
# ============================================================================


class SportStats(BaseModel):
    sport: str = Field(description="Sport name")
    workouts_count: int = Field(description="Total workouts in this sport")
    distance_km: float = Field(description="Total distance in km")
    distance_formatted: str = Field(description="Total distance formatted")
    duration_hours: float | None = Field(
        default=None, description="Total duration in hours"
    )
    duration_formatted: str = Field(description="Total duration formatted (HH:MM:SS)")
    calories_kcal: int = Field(description="Total energy consumed in kcal")


class UserStats(BaseModel):
    total_distance_km: float = Field(description="Lifetime total distance in km")
    total_distance_formatted: str = Field(
        description="Lifetime total distance formatted"
    )
    total_duration_hours: float = Field(description="Lifetime total time in hours")
    total_workouts: int = Field(description="Lifetime total number of workouts")
    total_calories_kcal: int = Field(description="Lifetime total calories in kcal")
    total_days: int = Field(description="Total registered active days")
    sports: list[SportStats] = Field(description="Breakdown per sport")

    @classmethod
    def from_api(cls, raw: dict[str, Any], imperial: bool = False) -> "UserStats":
        total_dist_m = _safe_float(raw.get("totalDistanceSum"), 0.0)
        total_time_s = _safe_float(raw.get("totalTimeSum"), 0.0)
        dist_val, dist_str = format_distance(total_dist_m, imperial=imperial)

        sports_list = []
        for s in raw.get("allStats") or []:
            if not isinstance(s, dict):
                continue
            s_dist_m = _safe_float(s.get("totalDistance"), 0.0)
            s_time_s = _safe_float(s.get("totalTime"), 0.0)
            s_dist_val, s_dist_str = format_distance(s_dist_m, imperial=imperial)
            sports_list.append(
                SportStats(
                    sport=ACTIVITY_MAPPING.get(s.get("_id", -1), "other"),
                    workouts_count=_safe_int(s.get("numberOfWorkouts"), 0),
                    distance_km=s_dist_val,
                    distance_formatted=s_dist_str,
                    duration_hours=round(s_time_s / 3600.0, 1),
                    duration_formatted=format_duration(s_time_s),
                    calories_kcal=_safe_int(s.get("energyConsumption"), 0),
                )
            )

        return cls(
            total_distance_km=dist_val,
            total_distance_formatted=dist_str,
            total_duration_hours=round(total_time_s / 3600.0, 1),
            total_workouts=_safe_int(raw.get("totalNumberOfWorkoutsSum"), 0),
            total_calories_kcal=_safe_int(raw.get("totalEnergyConsumptionSum"), 0),
            total_days=_safe_int(raw.get("totalDays"), 0),
            sports=sports_list,
        )


# ============================================================================
# 4. VO2Max & Fitness History
# ============================================================================


class VO2MaxRecord(BaseModel):
    date: str = Field(description="Date of workout (YYYY-MM-DD)")
    sport: str = Field(description="Sport performed, e.g. running, walking")
    workout_key: str = Field(description="Associated workout key")
    vo2_max: float = Field(description="VO2Max measurement in ml/kg/min")
    estimated_vo2_max: float | None = Field(
        default=None, description="Estimated VO2Max"
    )
    fitness_age: int | None = Field(default=None, description="Estimated fitness age")
    max_hr: int | None = Field(default=None, description="Max heart rate in bpm")


class VO2MaxHistory(BaseModel):
    records: list[VO2MaxRecord] = Field(description="Chronological VO2Max records")
    latest_vo2_max: float | None = Field(default=None, description="Most recent VO2Max")
    average_vo2_max: float | None = Field(
        default=None, description="Average VO2Max over recorded period"
    )
    latest_fitness_age: int | None = Field(
        default=None, description="Most recent estimated fitness age"
    )

    @classmethod
    def from_workouts(cls, raw_workouts: list[dict[str, Any]]) -> "VO2MaxHistory":
        records: list[VO2MaxRecord] = []
        for w in raw_workouts:
            exts = {
                e.get("type"): e
                for e in w.get("extensions") or []
                if isinstance(e, dict)
            }
            fitness_ext = exts.get("FitnessExtension")
            if not fitness_ext:
                continue
            vo2 = _opt_float(fitness_ext.get("vo2Max"))
            if vo2 is None:
                continue
            dt = _dt_from_ms(w.get("startTime"))
            date_str = dt.strftime("%Y-%m-%d") if dt else "Unknown"
            hr_data = w.get("hrdata")
            hr_dict = hr_data if isinstance(hr_data, dict) else {}
            max_hr_val = _opt_int(fitness_ext.get("maxHeartRate")) or _opt_int(
                hr_dict.get("hrmax") or hr_dict.get("max")
            )
            records.append(
                VO2MaxRecord(
                    date=date_str,
                    sport=ACTIVITY_MAPPING.get(w.get("activityId", -1), "other"),
                    workout_key=str(w.get("workoutKey", "")),
                    vo2_max=vo2,
                    estimated_vo2_max=_opt_float(fitness_ext.get("estimatedVo2Max")),
                    fitness_age=_opt_int(fitness_ext.get("fitnessAge")),
                    max_hr=max_hr_val if max_hr_val and max_hr_val > 0 else None,
                )
            )

        latest_vo2 = records[0].vo2_max if records else None
        avg_vo2 = (
            round(sum(r.vo2_max for r in records) / len(records), 1)
            if records
            else None
        )
        latest_age = next(
            (r.fitness_age for r in records if r.fitness_age is not None), None
        )

        return cls(
            records=records,
            latest_vo2_max=latest_vo2,
            average_vo2_max=avg_vo2,
            latest_fitness_age=latest_age,
        )


# ============================================================================
# 5. Training Summary (Aggregated over X days)
# ============================================================================


class TrainingSummary(BaseModel):
    days: int = Field(description="Number of days aggregated")
    workouts_count: int = Field(description="Total number of workouts in period")
    total_distance_km: float = Field(description="Total distance in km")
    total_distance_formatted: str = Field(description="Total distance formatted")
    total_duration_formatted: str = Field(
        description="Total duration formatted as HH:MM:SS"
    )
    total_calories_kcal: int = Field(description="Total calories burned in period")
    sports: list[SportStats] = Field(description="Breakdown per sport")

    @classmethod
    def from_workouts(
        cls,
        raw_workouts: list[dict[str, Any]],
        days: int = 7,
        imperial: bool = False,
    ) -> "TrainingSummary":
        sports_agg: dict[str, dict[str, Any]] = {}
        total_dist_m = 0.0
        total_time_s = 0.0
        total_cals = 0

        for w in raw_workouts:
            sport_name = ACTIVITY_MAPPING.get(w.get("activityId", -1), "other")
            dist_m = _safe_float(w.get("totalDistance"), 0.0)
            time_s = _safe_float(w.get("totalTime"), 0.0)
            cals = _safe_int(w.get("energyConsumption"), 0)

            total_dist_m += dist_m
            total_time_s += time_s
            total_cals += cals

            if sport_name not in sports_agg:
                sports_agg[sport_name] = {
                    "count": 0,
                    "dist_m": 0.0,
                    "time_s": 0.0,
                    "cals": 0,
                }
            sports_agg[sport_name]["count"] += 1
            sports_agg[sport_name]["dist_m"] += dist_m
            sports_agg[sport_name]["time_s"] += time_s
            sports_agg[sport_name]["cals"] += cals

        sports_list: list[SportStats] = []
        for sport_name, agg in sorted(
            sports_agg.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            s_dist_val, s_dist_str = format_distance(agg["dist_m"], imperial=imperial)
            sports_list.append(
                SportStats(
                    sport=sport_name,
                    workouts_count=agg["count"],
                    distance_km=s_dist_val,
                    distance_formatted=s_dist_str,
                    duration_formatted=format_duration(agg["time_s"]),
                    calories_kcal=agg["cals"],
                )
            )

        tot_dist_val, tot_dist_str = format_distance(total_dist_m, imperial=imperial)
        return cls(
            days=days,
            workouts_count=sum(agg["count"] for agg in sports_agg.values()),
            total_distance_km=tot_dist_val,
            total_distance_formatted=tot_dist_str,
            total_duration_formatted=format_duration(total_time_s),
            total_calories_kcal=total_cals,
            sports=sports_list,
        )


# ============================================================================
# 6. Training Load & Recovery Status
# ============================================================================


class TrainingLoadAndRecovery(BaseModel):
    latest_workout_key: str = Field(description="Latest workout identifier")
    latest_workout_date: str = Field(description="Date/time of latest workout")
    latest_sport: str = Field(description="Sport of latest workout")
    cumulative_recovery_hours: float = Field(
        description="Remaining body recovery needed in hours"
    )
    latest_workout_recovery_hours: float = Field(
        description="Recovery time generated by latest workout in hours"
    )
    training_stress_score: float | None = Field(
        default=None, description="TSS of latest workout"
    )
    peak_training_effect: float | None = Field(
        default=None, description="Peak Training Effect (PTE 1.0 - 5.0)"
    )
    peak_epoc: float | None = Field(default=None, description="Peak EPOC in ml/kg")
    impact_tag: str | None = Field(
        default=None, description="Suunto training impact tag, e.g. IMPACT_STRENGTH"
    )
    recovery_status: str = Field(
        description="Human-friendly status, e.g. 'Fully Recovered' or 'Fatigued'"
    )

    @classmethod
    def from_workout(cls, raw: dict[str, Any] | None) -> "TrainingLoadAndRecovery":
        if not raw:
            return cls(
                latest_workout_key="none",
                latest_workout_date="N/A",
                latest_sport="none",
                cumulative_recovery_hours=0.0,
                latest_workout_recovery_hours=0.0,
                training_stress_score=None,
                peak_training_effect=None,
                peak_epoc=None,
                impact_tag=None,
                recovery_status="Fully Recovered",
            )

        dt = _dt_from_ms(raw.get("startTime"))
        date_str = dt.isoformat() if dt else "Unknown"

        exts = {
            e.get("type"): e for e in raw.get("extensions") or [] if isinstance(e, dict)
        }
        summary_ext = exts.get("SummaryExtension", {})

        cum_rec_sec = _safe_float(raw.get("cumulativeRecoveryTime"), 0.0)
        cum_rec_hours = round(cum_rec_sec / 3600.0, 1)

        rec_sec = _safe_float(
            raw.get("recoveryTime") or summary_ext.get("recoveryTime"), 0.0
        )
        rec_hours = round(rec_sec / 3600.0, 1)

        tss_data = raw.get("tss")
        tss_val = (
            _opt_float(tss_data.get("trainingStressScore"))
            if isinstance(tss_data, dict)
            else None
        )

        tags = raw.get("suuntoTags")
        impact_tag = tags[0] if tags and isinstance(tags, list) else None

        if cum_rec_hours <= 0:
            status = "Fully Recovered"
        elif cum_rec_hours < 12:
            status = "Ready for Training"
        elif cum_rec_hours < 24:
            status = "Moderate Fatigue"
        elif cum_rec_hours < 48:
            status = "High Fatigue / Rest Advised"
        else:
            status = "Exhausted / Active Recovery Only"

        return cls(
            latest_workout_key=str(raw.get("workoutKey", "")),
            latest_workout_date=date_str,
            latest_sport=ACTIVITY_MAPPING.get(raw.get("activityId", -1), "other"),
            cumulative_recovery_hours=cum_rec_hours,
            latest_workout_recovery_hours=rec_hours,
            training_stress_score=round(tss_val, 1) if tss_val is not None else None,
            peak_training_effect=_opt_float(summary_ext.get("pte")),
            peak_epoc=_opt_float(summary_ext.get("peakEpoc")),
            impact_tag=impact_tag,
            recovery_status=status,
        )


# ============================================================================
# 7. Recent Activities Summary
# ============================================================================


class ActivityCount(BaseModel):
    sport: str = Field(description="Sport name")
    count: int = Field(description="Number of sessions")
    total_duration_formatted: str = Field(
        description="Total time spent in this activity"
    )
    last_performed: str = Field(description="Date when last performed")


class RecentActivitiesSummary(BaseModel):
    days: int = Field(description="Number of past days analyzed")
    total_sessions: int = Field(description="Total activity sessions recorded")
    activities: list[ActivityCount] = Field(description="Breakdown per activity")

    @classmethod
    def from_workouts(
        cls,
        raw_workouts: list[dict[str, Any]],
        days: int = 14,
    ) -> "RecentActivitiesSummary":
        sports_agg: dict[str, dict[str, Any]] = {}
        for w in raw_workouts:
            sport_name = ACTIVITY_MAPPING.get(w.get("activityId", -1), "other")
            time_s = _safe_float(w.get("totalTime"), 0.0)
            dt = _dt_from_ms(w.get("startTime"))
            date_str = dt.strftime("%Y-%m-%d") if dt else "Unknown"

            if sport_name not in sports_agg:
                sports_agg[sport_name] = {
                    "count": 0,
                    "time_s": 0.0,
                    "last_performed": date_str,
                }
            sports_agg[sport_name]["count"] += 1
            sports_agg[sport_name]["time_s"] += time_s

        activities_list: list[ActivityCount] = [
            ActivityCount(
                sport=sport,
                count=data["count"],
                total_duration_formatted=format_duration(data["time_s"]),
                last_performed=data["last_performed"],
            )
            for sport, data in sorted(
                sports_agg.items(), key=lambda x: x[1]["count"], reverse=True
            )
        ]

        return cls(
            days=days,
            total_sessions=sum(data["count"] for data in sports_agg.values()),
            activities=activities_list,
        )
