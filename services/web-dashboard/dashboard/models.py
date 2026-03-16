from django.db import models


class DiscordUser(models.Model):
    discord_id = models.TextField(unique=True)
    display_name = models.TextField()
    username = models.TextField(null=True, blank=True)
    avatar_url = models.TextField(null=True, blank=True)
    role = models.CharField(max_length=20, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return f"{self.display_name} ({self.discord_id})"


class Challenge(models.Model):
    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    rules = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'challenges'


class SpecialMission(models.Model):
    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    emoji = models.TextField(default='💥')
    bonus_points = models.IntegerField(default=0)
    min_distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_time_minutes = models.IntegerField(null=True, blank=True)
    activity_type_filter = models.TextField(null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_completions_per_user = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'special_missions'


class Activity(models.Model):
    user = models.ForeignKey(DiscordUser, on_delete=models.CASCADE, db_column='user_id')
    iid = models.TextField(unique=True)
    activity_type = models.TextField()
    distance_km = models.DecimalField(max_digits=10, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    elevation_m = models.IntegerField(null=True, blank=True)
    time_minutes = models.IntegerField(null=True, blank=True)
    pace = models.TextField(null=True, blank=True)
    heart_rate_avg = models.IntegerField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    base_points = models.IntegerField(default=0)
    weight_bonus_points = models.IntegerField(default=0)
    elevation_bonus_points = models.IntegerField(default=0)
    special_mission = models.ForeignKey(
        SpecialMission, on_delete=models.SET_NULL, null=True, blank=True, db_column='special_mission_id'
    )
    mission_bonus_points = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    challenge = models.ForeignKey(
        Challenge, on_delete=models.SET_NULL, null=True, blank=True, db_column='challenge_id'
    )
    created_at = models.DateTimeField()
    message_id = models.TextField(null=True, blank=True)
    message_timestamp = models.TextField(null=True, blank=True)
    ai_comment = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'activities'


class AirsoftEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('milsim', 'MilSim'),
        ('cqb', 'CQB'),
        ('woodland', 'Woodland'),
        ('scenario', 'Scenariuszowa'),
        ('other', 'Inne'),
    ]

    name = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    organizer = models.TextField(null=True, blank=True)
    event_type = models.TextField(choices=EVENT_TYPE_CHOICES, default='other')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.TextField(default='PLN')
    event_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'airsoft_events'

    def __str__(self):
        return f"{self.name} ({self.start_date.date()})"


class EventRegistration(models.Model):
    event = models.ForeignKey(AirsoftEvent, on_delete=models.CASCADE, db_column='event_id', related_name='registrations')
    user = models.ForeignKey(DiscordUser, on_delete=models.CASCADE, db_column='user_id')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'event_registrations'
        unique_together = (('event', 'user'),)

    def __str__(self):
        return f"{self.user.display_name} @ {self.event.name}"


class ActivityBonusLog(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, db_column='activity_id', related_name='manual_bonus_logs')
    points = models.IntegerField()
    note = models.TextField(null=True, blank=True)
    granted_by = models.ForeignKey(DiscordUser, on_delete=models.SET_NULL, null=True, blank=True, db_column='granted_by_user_id', related_name='granted_bonus_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'activity_bonus_logs'

    def __str__(self):
        return f"Bonus {self.points} pkt for activity {self.activity_id}"
