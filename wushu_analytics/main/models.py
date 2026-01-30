from django.db import models

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
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['competition', 'participant', 'ages_category', 'disciplines_category'],
                name='unique_performance'
            )
        ]
    
    def __str__(self):
        return f"{self.participant.name} - {self.origin_title}"