from django.db import models
from django.contrib.auth.models import User

class Competition(models.Model):
    link = models.CharField(max_length=500, blank=True, null=True)
    name = models.CharField(max_length=255)
    sity = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'sity', 'start_date', 'end_date'],
                name='unique_competition'
            )
        ]
    
    def __str__(self):
        return self.name

class Participant(models.Model):
    name = models.CharField(max_length=255)
    sity = models.CharField(max_length=100)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'sity'],
                name='unique_participant'
            )
        ]
    
    def __str__(self):
        return self.name

class DisciplineCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class AgeCategory(models.Model):
    min_ages = models.IntegerField()
    max_ages = models.IntegerField()
    sex = models.CharField(max_length=10)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['min_ages', 'max_ages', 'sex'],
                name='unique_age_category'
            )
        ]
    
    def __str__(self):
        return f"{self.sex} {self.min_ages}-{self.max_ages} лет"

class Performance(models.Model):
    carpet = models.IntegerField()
    origin_title = models.TextField()
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    ages_category = models.ForeignKey(AgeCategory, on_delete=models.SET_NULL, null=True)
    disciplines_category = models.ForeignKey(DisciplineCategory, on_delete=models.SET_NULL, null=True)
    est_start_datetime = models.DateTimeField()
    real_start_datetime = models.DateTimeField(null=True, blank=True)
    real_end_datetime = models.DateTimeField(null=True, blank=True)
    mark = models.FloatField(null=True, blank=True)
    place = models.IntegerField(null=True, blank=True, help_text="Занятое место (1, 2, 3...)")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['competition', 'participant', 'ages_category', 'disciplines_category'],
                name='unique_performance'
            )
        ]
    
    def __str__(self):
        return f"{self.participant.name} - {self.origin_title}"

class Coach(models.Model):
    """Модель тренера с доступом к аналитике определённых команд"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile')
    teams = models.TextField(help_text="Названия команд/городов через запятую", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Тренер"
        verbose_name_plural = "Тренеры"
    
    def __str__(self):
        return f"{self.user.username} - Тренер"
    
    def get_teams_list(self):
        """Возвращает список команд как список строк"""
        if not self.teams:
            return []
        return [team.strip() for team in self.teams.split(',') if team.strip()]
    
    def has_team_access(self, team_name):
        """Проверяет доступ к конкретной команде"""
        teams = self.get_teams_list()
        if not teams:  # Если команды не указаны, доступ ко всем
            return True
        return team_name.lower() in [t.lower() for t in teams]


class RegionStatistics(models.Model):
    """Сводная статистика по регионам для быстрой загрузки"""
    region = models.CharField(max_length=100, unique=True)
    participants_count = models.IntegerField(default=0)
    competitions_count = models.IntegerField(default=0)
    performances_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    bronze_count = models.IntegerField(default=0)
    avg_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Статистика региона"
        verbose_name_plural = "Статистика регионов"
    
    def __str__(self):
        return f"{self.region} - {self.gold_count} {self.silver_count} {self.bronze_count}"


class AthleteStatistics(models.Model):
    """Сводная статистика по спортсменам для быстрой загрузки"""
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='statistics')
    competitions_count = models.IntegerField(default=0)
    performances_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    bronze_count = models.IntegerField(default=0)
    avg_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Статистика спортсмена"
        verbose_name_plural = "Статистика спортсменов"
    
    def __str__(self):
        return f"{self.participant.name} - {self.gold_count} {self.silver_count} {self.bronze_count}"


class UserProfile(models.Model):
    """Профиль обычного пользователя с доступом к просмотру"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=255, null=True, blank=True)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    is_telegram_verified = models.BooleanField(default=False)
    telegram_verification_code = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
    
    def __str__(self):
        return f"{self.user.username} - {'✓' if self.is_telegram_verified else '✗'}"
    
    def generate_verification_code(self):
        """Генерирует код верификации для Telegram"""
        import secrets
        self.telegram_verification_code = secrets.token_urlsafe(16)
        self.save()
        return self.telegram_verification_code


class NotificationSubscription(models.Model):
    """Подписки пользователя на уведомления"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subscriptions')
    
    # Типы отслеживаемых объектов
    SUBSCRIPTION_TYPES = [
        ('competition', 'Соревнование'),
        ('participant', 'Участник'),
        ('region', 'Команда/Регион'),
        ('category', 'Категория соревнования'),
    ]
    
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)
    competition_id = models.IntegerField(null=True, blank=True, help_text="ID соревнования для типа 'competition' и 'category'")
    participant_id = models.IntegerField(null=True, blank=True, help_text="ID участника для типа 'participant'")
    region_name = models.CharField(max_length=100, null=True, blank=True, help_text="Название региона для типа 'region'")
    category_identifier = models.CharField(max_length=255, null=True, blank=True, help_text="Идентификатор категории для типа 'category'")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Подписка на уведомления"
        verbose_name_plural = "Подписки на уведомления"
        unique_together = [
            ['user_profile', 'subscription_type', 'competition_id', 'participant_id', 'region_name', 'category_identifier']
        ]
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.get_subscription_type_display()}"
    
    def get_target_name(self):
        """Возвращает имя отслеживаемого объекта"""
        if self.subscription_type == 'competition':
            try:
                from .models import Competition
                return Competition.objects.get(id=self.competition_id).name
            except Competition.DoesNotExist:
                return f"Соревнование #{self.competition_id}"
        elif self.subscription_type == 'participant':
            try:
                from .models import Participant
                return Participant.objects.get(id=self.participant_id).name
            except Participant.DoesNotExist:
                return f"Участник #{self.participant_id}"
        elif self.subscription_type == 'region':
            return self.region_name or "Неизвестный регион"
        elif self.subscription_type == 'category':
            return self.category_identifier or "Неизвестная категория"
        return "Неизвестный объект"