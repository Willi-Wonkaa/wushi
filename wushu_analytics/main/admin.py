from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Competition, Participant, DisciplineCategory, AgeCategory, Performance, Coach


class CoachInline(admin.StackedInline):
    model = Coach
    can_delete = False
    verbose_name_plural = 'Профиль тренера'


class CustomUserAdmin(UserAdmin):
    inlines = (CoachInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    
    def get_role(self, obj):
        if obj.is_superuser:
            return "Администратор"
        if hasattr(obj, 'coach_profile'):
            return "Тренер"
        return "Гость"
    get_role.short_description = 'Роль'


# Перерегистрируем User с новым админом
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ('user', 'teams', 'created_at')
    search_fields = ('user__username', 'teams')
    raw_id_fields = ('user',)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'sity', 'start_date', 'end_date')
    search_fields = ('name', 'sity')
    list_filter = ('start_date',)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'region')
    search_fields = ('name', 'region__region')


@admin.register(DisciplineCategory)
class DisciplineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(AgeCategory)
class AgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('sex', 'min_ages', 'max_ages')
    list_filter = ('sex',)


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('participant', 'performance_category_block', 'mark', 'place')
    list_filter = ('performance_category_block',)
    search_fields = ('participant__name', 'origin_title')
    raw_id_fields = ('participant', 'performance_category_block')
