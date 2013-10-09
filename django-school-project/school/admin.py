from .models import *
from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse


class StudentEnrolmentsInline(admin.TabularInline):
    '''Shows enrolments with the student'''
    model = Enrolment
    extra = 0
    def queryset(self, request):
        current = Semester.working(request)
        qs = super(StudentEnrolmentsInline, self).queryset(request)
        return qs.filter(school_class__cycle=current)

    def class_link(self, instance):
        url = reverse('admin:%s_%s_change' % (
            instance._meta.app_label,  instance.school_class._meta.module_name),  args=[instance.school_class.id] )
        return mark_safe(u'<a href="{u}">{s}</a>'.format(u=url,s=instance.school_class))

    fields = ('class_link',)
    readonly_fields = ('class_link',)


class StudentAdmin(admin.ModelAdmin):
    list_display = ('timetable_id', 'first_name', 'last_name', 'network_id', 'gender', 'title', 'year_level', 'start_date',
                    'govt_student_code', 'house_group', 'mentor_group')
    list_filter = ('is_current', 'year_level', 'house_group')
    inlines = (StudentEnrolmentsInline,)
    exclude = ('auth',)

    def changelist_view(self, request, extra_context=None):
        if not request.GET.has_key('is_current__exact'):
            q = request.GET.copy()
            q['is_current__exact'] = '1'
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(StudentAdmin,self).changelist_view(request, extra_context=extra_context)

class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('timetable_id', 'first_name', 'last_name', 'network_id', 'gender', 'title')
    list_filter = ('is_current',)
    #inlines = [IsTeacherInline]
    exclude = ('auth',)

class SchoolClassStudentsInline(admin.TabularInline):
    model = Enrolment

    def student_link(self, instance):
        url = reverse('admin:%s_%s_change' % (
            instance._meta.app_label,  instance.student._meta.module_name),  args=[instance.student.id] )
        return mark_safe(u'<a href="{u}">{s}</a>'.format(u=url,s=instance.student))

    fields = ('student_link',)
    readonly_fields = ('student_link',)
    extra = 0

class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'teacher', 'subject', 'cycle')
    inlines = (SchoolClassStudentsInline,)

    def subject_link(self, instance):
        url = reverse('admin:%s_%s_change' % (
            instance._meta.app_label,  instance.subject._meta.module_name),  args=[instance.subject.id] )
        return mark_safe(u'<a href="{u}">{s}</a>'.format(u=url,s=instance.subject))

    readonly_fields = ('subject_link',)

class SubjectSchoolClassInline(admin.TabularInline):
    model = SchoolClass

    def class_link(self, instance):
        url = reverse('admin:%s_%s_change' % (
            instance._meta.app_label, instance._meta.module_name), args=[instance.id])
        return mark_safe(u'<a href="{u}">{s}</a>'.format(u=url,s=instance))

    fields = ('class_link',)
    readonly_fields = ('class_link',)
    extra = 0

class SubjectAdmin(admin.ModelAdmin):
    inlines = (SubjectSchoolClassInline,)
    filter_horizontal = ('leaders', 'badges')

class DepartmentAdmin(admin.ModelAdmin):
    filter_horizontal = ('leaders', 'members')

admin.site.register(Student, StudentAdmin)
admin.site.register(StaffMember, StaffMemberAdmin)
admin.site.register(SchoolClass, SchoolClassAdmin)
admin.site.register(Semester)
admin.site.register(Enrolment)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Department, DepartmentAdmin)

