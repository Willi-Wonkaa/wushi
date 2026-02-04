from django.db import models
from django.contrib.auth.models import User



# какой максимальный разряд можно получить на этом соревновании (кмс, мс...)
class CompetitionLevel(models.Model):
    competition_level = models.IntegerField(unique=True)
    level_description = models.TextField()
    
    def __str__(self):
        return str(self.competition_level)



class DisciplineCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class AgeCategory(models.Model):
    original_text = models.TextField()
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





class Regions(models.Model):
    region = models.CharField(max_length=100, unique=True)

    participants_count = models.IntegerField(default=0)
    competitions_count = models.IntegerField(default=0)
    performances_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    bronze_count = models.IntegerField(default=0)
    

    def __str__(self):
        return self.region


class Participant(models.Model):
    name = models.CharField(max_length=255)
    region = models.ForeignKey(Regions, on_delete=models.SET_NULL, null=True)

    competitions_count = models.IntegerField(default=0)
    performances_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    bronze_count = models.IntegerField(default=0)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'region'],
                name='unique_participant'
            )
        ]
    
    def __str__(self):
        return self.name





class Competition(models.Model):
    link = models.CharField(max_length=500, blank=True, null=True)
    name = models.CharField(max_length=255)
    sity = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()

    competiton_active_status = models.TextField(blank=True, null=False, default='unknown')
    competition_level = models.ForeignKey(CompetitionLevel, on_delete=models.SET_NULL, null=True)

    regions_count = models.IntegerField(default=0)
    participants_count = models.IntegerField(default=0)
    performances_count = models.IntegerField(default=0)
    gold_count = models.IntegerField(default=0)
    silver_count = models.IntegerField(default=0)
    bronze_count = models.IntegerField(default=0)

    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'sity', 'start_date', 'end_date'],
                name='unique_competition'
            )
        ]
    
    def __str__(self):
        return self.name


class PerformanceCarpet(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    carpet = models.IntegerField(null=False, default=1)
    
    def __str__(self):
        return f"{self.competition} - {self.carpet}"



class PerformanceCategoryBlock(models.Model):
    performance_category_carpet = models.ForeignKey(PerformanceCarpet, on_delete=models.CASCADE)

    age_category = models.ForeignKey(AgeCategory, on_delete=models.SET_NULL, null=True)
    discipline_category = models.ForeignKey(DisciplineCategory, on_delete=models.SET_NULL, null=True)

    participants_count = models.IntegerField(default=0)
    number_at_carpet = models.IntegerField(default=0)
    status = models.CharField(max_length=50, blank=True, null=False, default='unknown')
    
    def __str__(self):
        return f"{self.performance_category_carpet} - {self.age_category} - {self.discipline_category}"



class Performance(models.Model):
    origin_title = models.TextField()
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    performance_category_block = models.ForeignKey(PerformanceCategoryBlock, on_delete=models.SET_NULL, null=True)

    est_start_datetime = models.DateTimeField()
    real_start_datetime = models.DateTimeField(null=True, blank=True)
    mark = models.FloatField(null=True, blank=True)
    place = models.IntegerField(null=True, blank=True)
    number_at_block = models.IntegerField(default=0)

    
    def __str__(self):
        return f"{self.participant.name} - {self.origin_title}"





# =========== autorisations tables

class UserProfile(models.Model):
    """Профиль обычного пользователя с доступом к просмотру"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=255, null=True, blank=True)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
    
    def __str__(self):
        return f"{self.telegram_username} - {self.telegram_id}"



class Coach(models.Model):
    """Модель тренера с доступом к аналитике определённых команд"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile')
    teams = models.TextField(help_text="Названия команд/городов через запятую", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    telergam_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
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






class TrackedParticipants(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tracked_participant = models.ForeignKey(Participant, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile.telegram_username} - tracked participant: {self.tracked_participant.name}"

    

class TrackedCompetition(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tracked_competition = models.ForeignKey(Competition, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile.telegram_username} - tracked competition: {self.tracked_competition.name}"

    

class TrackedRegion(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tracked_region = models.ForeignKey(Regions, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile.telegram_username} - tracked region: {self.tracked_region.name}"
    


class TrackedCategoryBlock(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tracked_category_block = models.ForeignKey(PerformanceCategoryBlock, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile.telegram_username} - tracked category block: {self.tracked_category_block.name}"


class TrackedCarpet(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    tracked_carpet = models.ForeignKey(PerformanceCarpet, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_profile.telegram_username} - tracked carpet: {self.tracked_carpet.name}"
