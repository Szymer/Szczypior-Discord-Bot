from rest_framework import serializers
from django.conf import settings
from .models import Activity, DiscordUser, Challenge, SpecialMission, AirsoftEvent


class ChallengeSerializer(serializers.ModelSerializer):
    startDate = serializers.DateTimeField(source="start_date", format="%Y-%m-%d")
    endDate = serializers.DateTimeField(source="end_date", format="%Y-%m-%d")
    isActive = serializers.BooleanField(source="is_active")
    emoji = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    bonusPoints = serializers.SerializerMethodField()
    pointsRules = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id",
            "name",
            "description",
            "emoji",
            "startDate",
            "endDate",
            "goal",
            "bonusPoints",
            "pointsRules",
            "isActive",
        ]

    def get_emoji(self, obj):
        return (obj.rules or {}).get("emoji", "🏆")

    def get_goal(self, obj):
        return (obj.rules or {}).get("goal", "")

    def get_bonusPoints(self, obj):
        return (obj.rules or {}).get("bonus_points", 0)

    def get_pointsRules(self, obj):
        rules = (obj.rules or {}).get("points_rules")
        return rules if isinstance(rules, dict) else None


class ActivitySerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    userId = serializers.ReadOnlyField(source="user.discord_id")
    distanceKm = serializers.FloatField(source="distance_km")
    loadKg = serializers.FloatField(source="weight_kg")
    elevationGain = serializers.IntegerField(source="elevation_m")
    durationMin = serializers.IntegerField(source="time_minutes")
    paceMinPerKm = serializers.SerializerMethodField(method_name="get_paceMinPerKm")
    heartRateAvg = serializers.IntegerField(source="heart_rate_avg")
    pointsEarned = serializers.IntegerField(source="total_points")
    basePoints = serializers.IntegerField(source="base_points")
    bonusPoints = serializers.SerializerMethodField(method_name="get_bonus_points")
    weightBonusPoints = serializers.IntegerField(source="weight_bonus_points")
    elevationBonusPoints = serializers.IntegerField(source="elevation_bonus_points")
    missionBonusPoints = serializers.IntegerField(source="mission_bonus_points")
    date = serializers.SerializerMethodField()
    challengeId = serializers.IntegerField(source="challenge_id")

    class Meta:
        model = Activity
        fields = [
            "id",
            "userId",
            "type",
            "date",
            "distanceKm",
            "loadKg",
            "elevationGain",
            "durationMin",
            "paceMinPerKm",
            "heartRateAvg",
            "calories",
            "pointsEarned",
            "basePoints",
            "bonusPoints",
            "weightBonusPoints",
            "elevationBonusPoints",
            "missionBonusPoints",
            "ai_comment",
            "challengeId",
        ]

    def get_type(self, obj):
        mapping = getattr(settings, "ACTIVITY_MAP", {})
        return mapping.get(obj.activity_type, obj.activity_type)

    def get_date(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_bonus_points(self, obj):
        return (
            obj.weight_bonus_points
            + obj.elevation_bonus_points
            + obj.mission_bonus_points
        )

    def get_paceMinPerKm(self, obj):
        if not obj.pace:
            return None
        try:
            # pace stored as "MM:SS" → convert to float minutes
            parts = str(obj.pace).split(":")
            return round(int(parts[0]) + int(parts[1]) / 60, 2)
        except Exception:
            return None


class PlayerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="discord_id")
    username = serializers.CharField(source="display_name")
    totalPoints = serializers.SerializerMethodField()
    totalDistanceKm = serializers.SerializerMethodField()
    totalActivities = serializers.SerializerMethodField()
    totalDurationMin = serializers.SerializerMethodField()
    favoriteActivity = serializers.SerializerMethodField()
    runningKm = serializers.SerializerMethodField()
    swimmingKm = serializers.SerializerMethodField()
    cyclingKm = serializers.SerializerMethodField()
    walkingKm = serializers.SerializerMethodField()
    otherKm = serializers.SerializerMethodField()

    class Meta:
        model = DiscordUser
        fields = [
            "id",
            "username",
            "avatar_url",
            "totalPoints",
            "totalDistanceKm",
            "totalActivities",
            "totalDurationMin",
            "favoriteActivity",
            "runningKm",
            "swimmingKm",
            "cyclingKm",
            "walkingKm",
            "otherKm",
        ]

    def _acts(self, obj):
        acts = obj.activity_set.all()
        challenge_id = self.context.get("challenge_id")
        if challenge_id is not None:
            acts = acts.filter(challenge_id=challenge_id)
        return list(acts)

    def get_totalPoints(self, obj):
        return sum(a.total_points for a in self._acts(obj))

    def get_totalDistanceKm(self, obj):
        return round(float(sum(a.distance_km for a in self._acts(obj))), 2)

    def get_totalActivities(self, obj):
        return len(self._acts(obj))

    def get_totalDurationMin(self, obj):
        return sum(a.time_minutes or 0 for a in self._acts(obj))

    def get_favoriteActivity(self, obj):
        mapping = getattr(settings, "ACTIVITY_MAP", {})
        acts = self._acts(obj)
        if not acts:
            return "running_terrain"
        from collections import Counter

        most_common = Counter(a.activity_type for a in acts).most_common(1)[0][0]
        return mapping.get(most_common, most_common)

    def _km_for_types(self, obj, db_types):
        return round(
            float(
                sum(
                    a.distance_km
                    for a in self._acts(obj)
                    if a.activity_type in db_types
                )
            ),
            2,
        )

    def get_runningKm(self, obj):
        return self._km_for_types(obj, ["bieganie_teren", "bieganie_bieznia"])

    def get_swimmingKm(self, obj):
        return self._km_for_types(obj, ["plywanie"])

    def get_cyclingKm(self, obj):
        return self._km_for_types(obj, ["rower"])

    def get_walkingKm(self, obj):
        return self._km_for_types(obj, ["spacer"])

    def get_otherKm(self, obj):
        return self._km_for_types(obj, ["cardio"])


class PlayerRankingSerializer(PlayerSerializer):
    rank = serializers.SerializerMethodField()
    pointsDiff = serializers.SerializerMethodField()
    bestPaceMinPerKm = serializers.SerializerMethodField()

    def get_rank(self, obj):
        return None

    def get_pointsDiff(self, obj):
        return None

    def get_bestPaceMinPerKm(self, obj):
        return None

    bestPaceMinPerKm = serializers.FloatField(allow_null=True)

    class Meta(PlayerSerializer.Meta):
        fields = PlayerSerializer.Meta.fields + [
            "rank",
            "pointsDiff",
            "bestPaceMinPerKm",
        ]


class StatsSummarySerializer(serializers.Serializer):
    avg5Points = serializers.IntegerField()
    bestActivityPoints = serializers.IntegerField()
    bestActivityDate = serializers.CharField(allow_null=True)
    avgRunningPace = serializers.FloatField(allow_null=True)
    totalDurationMin = serializers.IntegerField()


class WeeklyStatsPointSerializer(serializers.Serializer):
    name = serializers.CharField()
    points = serializers.IntegerField()
    distance = serializers.FloatField()


class ActivityDistributionSerializer(serializers.Serializer):
    type = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    distance = serializers.FloatField()
    points = serializers.IntegerField()


class AsgEventSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    type = serializers.CharField(source="event_type")
    maxParticipants = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    emoji = serializers.SerializerMethodField()

    class Meta:
        model = AirsoftEvent
        fields = [
            "id",
            "name",
            "date",
            "location",
            "description",
            "organizer",
            "maxParticipants",
            "participants",
            "type",
            "emoji",
        ]

    def get_date(self, obj):
        return obj.start_date.strftime("%Y-%m-%d")

    def get_maxParticipants(self, obj):
        return None

    def get_participants(self, obj):
        return [
            p.user.discord_id for p in obj.registrations.select_related("user").all()
        ]

    def get_emoji(self, obj):
        return {
            "milsim": "🎖️",
            "cqb": "🏢",
            "woodland": "🌲",
            "scenario": "📜",
            "other": "🔫",
        }.get(obj.event_type, "🔫")


class ChallengeAdminSerializer(serializers.ModelSerializer):
    startDate = serializers.DateTimeField(source="start_date", format="%Y-%m-%d")
    endDate = serializers.DateTimeField(source="end_date", format="%Y-%m-%d")
    isActive = serializers.BooleanField(source="is_active")
    emoji = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    bonusPoints = serializers.SerializerMethodField()
    pointsRules = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id",
            "name",
            "description",
            "emoji",
            "startDate",
            "endDate",
            "goal",
            "bonusPoints",
            "pointsRules",
            "isActive",
        ]

    def get_emoji(self, obj):
        return (obj.rules or {}).get("emoji", "🏆")

    def get_goal(self, obj):
        return (obj.rules or {}).get("goal", "")

    def get_bonusPoints(self, obj):
        return (obj.rules or {}).get("bonus_points", 0)

    def get_pointsRules(self, obj):
        rules = (obj.rules or {}).get("points_rules")
        return rules if isinstance(rules, dict) else None
