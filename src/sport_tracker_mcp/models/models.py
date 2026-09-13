from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from ..constants import ACTIVITY_MAPPING
from ..formatting import (
    format_distance,
    format_duration,
    format_pace,
    format_speed,
    within_window,
)

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
        if not isinstance(raw, dict):
            return None

        workout_key = raw.get("workoutKey") or raw.get("key")
        start_time_raw = raw.get("startTime")
        if not workout_key or start_time_raw is None:
            return None

        try:
            start_dt = datetime.fromtimestamp(
                float(start_time_raw) / 1000.0, tz=timezone.utc
            )
        except ValueError, TypeError, OSError:
            return None

        dist_m = float(raw.get("totalDistance", 0.0) or 0.0)
        time_s = float(raw.get("totalTime", 0.0) or 0.0)
        speed_ms = float(raw.get("avgSpeed", 0.0) or 0.0)
        dist_val, dist_str = format_distance(dist_m, imperial=imperial)
        _, speed_str = format_speed(speed_ms, imperial=imperial)
        pace_str = format_pace(speed_ms, imperial=imperial)
        hr_data = raw.get("hrdata") or {}
        avg_hr = hr_data.get("avg") if isinstance(hr_data, dict) else None
        max_hr = (
            hr_data.get("hrmax") or hr_data.get("max")
            if isinstance(hr_data, dict)
            else None
        )
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
            calories_kcal=raw.get("energyConsumption"),
            avg_hr=avg_hr if avg_hr and avg_hr > 0 else None,
            max_hr=max_hr if max_hr and max_hr > 0 else None,
            step_count=raw.get("stepCount") if raw.get("stepCount", 0) > 0 else None,
        )


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

    @classmethod
    def from_api(
        cls, raw: dict[str, Any], imperial: bool = False
    ) -> "WorkoutDetail | None":
        base = WorkoutSummary.from_api(raw, imperial=imperial)
        if base is None:
            return None

        max_speed_ms = float(raw.get("maxSpeed", 0.0) or 0.0)
        _, max_speed_str = format_speed(max_speed_ms, imperial=imperial)

        extensions: list[dict[str, Any]] = raw.get("extensions") or []
        summary_ext: dict[str, Any] = next(
            (e for e in extensions if e.get("type") == "SummaryExtension"), {}
        )
        intensity_ext: dict[str, Any] = next(
            (e for e in extensions if e.get("type") == "IntensityExtension"), {}
        )

        rec_sec = raw.get("recoveryTime") or summary_ext.get("recoveryTime")
        rec_hours = round(rec_sec / 3600.0, 1) if rec_sec else None

        cum_rec_sec = raw.get("cumulativeRecoveryTime")
        cum_rec_hours = round(cum_rec_sec / 3600.0, 1) if cum_rec_sec else None

        tss_data = raw.get("tss") or {}
        tss_val = (
            tss_data.get("trainingStressScore") if isinstance(tss_data, dict) else None
        )

        gear_data = summary_ext.get("gear") or {}
        gear_name = (
            gear_data.get("displayName") or gear_data.get("name")
            if isinstance(gear_data, dict)
            else None
        )

        hr_zones: dict[str, str] | None = None
        zones_data = (
            intensity_ext.get("zones", {}).get("heartRate")
            if isinstance(intensity_ext, dict)
            else None
        )
        if isinstance(zones_data, dict):
            hr_zones = {}
            for zone_key in ["zone1", "zone2", "zone3", "zone4", "zone5"]:
                if zone_key in zones_data:
                    zone_secs = float(zones_data[zone_key].get("totalTime") or 0.0)
                    hr_zones[zone_key] = format_duration(zone_secs)

        return cls(
            **base.model_dump(),
            description=raw.get("description") or None,
            max_speed_formatted=max_speed_str,
            ascent_meters=float(
                raw.get("totalAscent") or summary_ext.get("ascent") or 0.0
            ),
            descent_meters=float(
                raw.get("totalDescent") or summary_ext.get("descent") or 0.0
            ),
            recovery_time_hours=rec_hours,
            cumulative_recovery_hours=cum_rec_hours,
            training_stress_score=round(tss_val, 1) if tss_val is not None else None,
            peak_training_effect=summary_ext.get("pte"),
            peak_epoc=summary_ext.get("peakEpoc"),
            gear=gear_name,
            heart_rate_zones=hr_zones,
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

        start_time_raw = raw.get("startTime")
        start_time_iso = None
        if start_time_raw is not None:
            try:
                start_time_iso = datetime.fromtimestamp(
                    float(start_time_raw) / 1000.0, tz=timezone.utc
                ).isoformat()
            except ValueError, OSError:
                start_time_iso = None

        dist_m = float(raw.get("totalDistance") or 0.0)
        time_s = float(raw.get("totalTime") or 0.0)
        speed_ms = float(raw.get("avgSpeed") or 0.0)

        _, dist_str = format_distance(dist_m, imperial=imperial)
        _, speed_str = format_speed(speed_ms, imperial=imperial)

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
            likes_count=int(raw.get("reactionCount") or 0),
            comments_count=int(raw.get("commentCount") or 0),
        )


# ============================================================================
# 3. User & Lifetime Stats
# ============================================================================


class SportStats(BaseModel):
    sport: str = Field(description="Sport name")
    workouts_count: int = Field(description="Total workouts in this sport")
    distance_km: float = Field(description="Total distance in km")
    distance_formatted: str = Field(description="Total distance formatted")
    duration_hours: float = Field(description="Total duration in hours")
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
        total_dist_m = float(raw.get("totalDistanceSum") or 0.0)
        total_time_s = float(raw.get("totalTimeSum") or 0.0)
        dist_val, dist_str = format_distance(total_dist_m, imperial=imperial)

        sports_list = []
        for s in raw.get("allStats") or []:
            s_dist_m = float(s.get("totalDistance") or 0.0)
            s_time_s = float(s.get("totalTime") or 0.0)
            s_dist_val, s_dist_str = format_distance(s_dist_m, imperial=imperial)
            sports_list.append(
                SportStats(
                    sport=ACTIVITY_MAPPING.get(s.get("_id", -1), "other"),
                    workouts_count=int(s.get("numberOfWorkouts") or 0),
                    distance_km=s_dist_val,
                    distance_formatted=s_dist_str,
                    duration_hours=round(s_time_s / 3600.0, 1),
                    duration_formatted=format_duration(s_time_s),
                    calories_kcal=int(s.get("energyConsumption") or 0),
                )
            )

        return cls(
            total_distance_km=dist_val,
            total_distance_formatted=dist_str,
            total_duration_hours=round(total_time_s / 3600.0, 1),
            total_workouts=int(raw.get("totalNumberOfWorkoutsSum") or 0),
            total_calories_kcal=int(raw.get("totalEnergyConsumptionSum") or 0),
            total_days=int(raw.get("totalDays") or 0),
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
            exts: list[dict[str, Any]] = w.get("extensions") or []
            fitness_ext = next(
                (e for e in exts if e.get("type") == "FitnessExtension"), None
            )
            if not fitness_ext:
                continue
            vo2 = fitness_ext.get("vo2Max")
            if vo2 is None:
                continue
            start_ms = w.get("startTime", 0)
            date_str = (
                datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).strftime(
                    "%Y-%m-%d"
                )
                if start_ms
                else "Unknown"
            )
            hr_data = w.get("hrdata") or {}
            max_hr = fitness_ext.get("maxHeartRate") or (
                hr_data.get("hrmax") if isinstance(hr_data, dict) else None
            )
            records.append(
                VO2MaxRecord(
                    date=date_str,
                    sport=ACTIVITY_MAPPING.get(w.get("activityId", -1), "other"),
                    workout_key=w.get("workoutKey", ""),
                    vo2_max=float(vo2),
                    estimated_vo2_max=(
                        float(fitness_ext["estimatedVo2Max"])
                        if fitness_ext.get("estimatedVo2Max") is not None
                        else None
                    ),
                    fitness_age=(
                        int(fitness_ext["fitnessAge"])
                        if fitness_ext.get("fitnessAge") is not None
                        else None
                    ),
                    max_hr=int(max_hr) if max_hr else None,
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


class SportTrainingSummary(BaseModel):
    sport: str = Field(description="Sport name")
    workouts_count: int = Field(description="Number of workouts in this sport")
    distance_km: float = Field(description="Total distance in km")
    distance_formatted: str = Field(description="Total distance formatted")
    duration_formatted: str = Field(description="Total duration formatted as HH:MM:SS")
    calories_kcal: int = Field(description="Total calories in kcal")


class TrainingSummary(BaseModel):
    days: int = Field(description="Number of days aggregated")
    workouts_count: int = Field(description="Total number of workouts in period")
    total_distance_km: float = Field(description="Total distance in km")
    total_distance_formatted: str = Field(description="Total distance formatted")
    total_duration_formatted: str = Field(
        description="Total duration formatted as HH:MM:SS"
    )
    total_calories_kcal: int = Field(description="Total calories burned in period")
    sports: list[SportTrainingSummary] = Field(description="Breakdown per sport")

    @classmethod
    def from_workouts(
        cls,
        raw_workouts: list[dict[str, Any]],
        days: int = 7,
        imperial: bool = False,
        now_ts: float | None = None,
    ) -> "TrainingSummary":
        valid_workouts = within_window(raw_workouts, days=days, now_ts=now_ts)

        sports_agg: dict[str, dict[str, Any]] = {}
        total_dist_m = 0.0
        total_time_s = 0.0
        total_cals = 0

        for w in valid_workouts:
            sport_name = ACTIVITY_MAPPING.get(w.get("activityId", -1), "other")
            dist_m = float(w.get("totalDistance") or 0.0)
            time_s = float(w.get("totalTime") or 0.0)
            cals = int(w.get("energyConsumption") or 0)

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

        sports_list: list[SportTrainingSummary] = []
        for sport_name, agg in sorted(
            sports_agg.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            s_dist_val, s_dist_str = format_distance(agg["dist_m"], imperial=imperial)
            sports_list.append(
                SportTrainingSummary(
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
            workouts_count=len(valid_workouts),
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

        start_ms = raw.get("startTime", 0)
        date_str = (
            datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).isoformat()
            if start_ms
            else "Unknown"
        )
        extensions: list[dict[str, Any]] = raw.get("extensions") or []
        summary_ext: dict[str, Any] = next(
            (e for e in extensions if e.get("type") == "SummaryExtension"), {}
        )
        cum_rec_sec = raw.get("cumulativeRecoveryTime", 0) or 0
        cum_rec_hours = round(cum_rec_sec / 3600.0, 1)
        rec_sec = raw.get("recoveryTime", 0) or summary_ext.get("recoveryTime", 0) or 0
        rec_hours = round(rec_sec / 3600.0, 1)

        tss_data = raw.get("tss") or {}
        tss_val = (
            tss_data.get("trainingStressScore") if isinstance(tss_data, dict) else None
        )

        tags = raw.get("suuntoTags") or []
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
            latest_workout_key=raw.get("workoutKey", ""),
            latest_workout_date=date_str,
            latest_sport=ACTIVITY_MAPPING.get(raw.get("activityId", -1), "other"),
            cumulative_recovery_hours=cum_rec_hours,
            latest_workout_recovery_hours=rec_hours,
            training_stress_score=round(tss_val, 1) if tss_val is not None else None,
            peak_training_effect=summary_ext.get("pte"),
            peak_epoc=summary_ext.get("peakEpoc"),
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
        now_ts: float | None = None,
    ) -> "RecentActivitiesSummary":
        valid_workouts = within_window(raw_workouts, days=days, now_ts=now_ts)

        sports_agg: dict[str, dict[str, Any]] = {}
        for w in valid_workouts:
            sport_name = ACTIVITY_MAPPING.get(w.get("activityId", -1), "other")
            time_s = float(w.get("totalTime") or 0.0)
            start_ms = w.get("startTime")
            date_str = (
                datetime.fromtimestamp(
                    float(start_ms) / 1000.0, tz=timezone.utc
                ).strftime("%Y-%m-%d")
                if start_ms is not None
                else "Unknown"
            )

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
            total_sessions=len(valid_workouts),
            activities=activities_list,
        )
