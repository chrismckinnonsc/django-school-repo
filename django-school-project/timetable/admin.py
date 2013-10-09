from .models import *
from django.contrib import admin

class DayAdmin(admin.ModelAdmin):
    pass
    #filter_horizontal = ('periods',)

class PeriodInline(admin.TabularInline):
    model = Period
    extra = 5

class PeriodSetAdmin(admin.ModelAdmin):
    inlines = (PeriodInline,)



DateAdmin = DayAdmin
admin.site.register(Day, DayAdmin)
#admin.site.register(Period)
admin.site.register(PeriodSet, PeriodSetAdmin)
admin.site.register(Date, DateAdmin)
admin.site.register(Term)
