from django.db import models
from django.conf import settings
from school.models import AuthUser, SchoolClass, AbstractCycle, Location
from django.core.exceptions import ObjectDoesNotExist
import logging
logger = logging.getLogger(__name__)

import datetime

class Term(AbstractCycle):
    start_week = models.SmallIntegerField(choices=settings.TIMETABLE_WEEKS)
    #semester = models.ForeignKey('Semester') #TODO - might need to get rid of this as a semester can cross 2 terms


#TODO - google mixin?
class BaseEvent(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    attendees = models.ManyToManyField(AuthUser, blank=True, null=True)
    location = models.ForeignKey(Location, blank=True) #TODO - non-room location?

    def save(self, *args, **kwargs):
        super(BaseEvent, self).save(*args, **kwargs)
        #TODO - update Google Cal
    class Meta:
        abstract = True


#TODO - do we need to optionally have a foreignkey to a Date here?
class Event(models.Model):
    date = models.DateField()
    entry = models.ForeignKey('Entry')
    google_event_id = models.CharField(max_length=100, blank=True)

    def start(self, date_obj=None):
        if date_obj:
            start_time = date_obj.get_period(self.entry.period.code).start
        else:
            start_time = Date.objects.get_period(self.date, self.entry.period.code).start
        return datetime.datetime.combine(self.date, start_time)

    def end(self, date_obj=None):
        if date_obj:
            end_time = date_obj.get_period(self.entry.period.code).end
        else:
            end_time = Date.objects.get_period(self.date, self.entry.period.code).end
        return datetime.datetime.combine(self.date, end_time)

    def attendees(self):
        attendees = []
        #for s in self.entry.school_class.students.all():
        #    attendees.append(s.email)
        attendees.append(self.entry.school_class.teacher.email)
        return attendees

    def location(self):
        try:
            return self.entry.location
        except Location.DoesNotExist:
            return ''

    def save(self, *args, **kwargs):
        date_obj = kwargs.pop('date_obj', None)
        super(Event, self).save(*args, **kwargs)
        from sync import google_tasks
        google_tasks.google_task('google_update_timetable_event', tt_event=self, date_obj=date_obj)


class Entry(models.Model):
    day = models.ForeignKey('Day')
    period = models.ForeignKey('Period')
    location = models.ForeignKey(Location, blank=True, null=True) #TODO - non-room location?
    school_class = models.ForeignKey(SchoolClass)

    def save(self, *args, **kwargs):
        request = kwargs.pop('request', None)

        super(Entry, self).save(*args, **kwargs)
        cursor_date = self.school_class.cycle.start_date
        while cursor_date <= self.school_class.cycle.end_date:
            day = Date.objects.get_day(cursor_date)
            if day == self.day:
                ev, c = Event.objects.get_or_create(date=cursor_date, entry=self)
                if not c:
                    ev.save()  # trigger update of event
            cursor_date += datetime.timedelta(days=1)

    def __unicode__(self):
        return "TT Entry: Day %s, Period %s, Room %s, Class %s" % (self.day.code, self.period.code, self.location.code,
                                                                   self.school_class.code)


class Period(models.Model):
    code = models.CharField(max_length=20)  # TODO - set choices
    name = models.CharField(max_length=100)  # TODO - set choices
    start = models.TimeField()
    end = models.TimeField()
    periodset = models.ForeignKey("PeriodSet", null=True)

    def __unicode__(self):
        return "Period %s: %s-%s" % (self.name, self.start, self.end)
    class Meta:
        ordering = ['code']


#TODO - need to replace Day->Period and Date->Period references with PeriodSet
class PeriodSet(models.Model):
    #periods = models.ManyToManyField(Period)
    description = models.CharField(max_length=100)
    def __unicode__(self):
        return self.description


class Day(models.Model):
    #TODO - Can probably remove this to a static list in settings.py as it shouldn't change once it's configured
    DAYS = ((0,'Monday'), (1,'Tuesday'), (2,'Wednesday'), (3,'Thursday'), (4,'Friday'), (5,'Saturday'), (6,'Sunday'))
    code = models.CharField(max_length=20, unique=True)
    day_of_week = models.SmallIntegerField(choices=DAYS)
    week = models.SmallIntegerField(choices=settings.TIMETABLE_WEEKS)
    periodset = models.ForeignKey(PeriodSet)
    #periods = models.ManyToManyField(Period, blank=True, null=True)

    def __unicode__(self):
        return "Day %s: %s Week %s" % (self.code, self.get_day_of_week_display(), self.get_week_display())


class DateManager(models.Manager):
    def get_day(self, date):
        """ Returns the Day for the specified date """
        try:
            term = Term.objects.get(start_date__lte=date, end_date__gte=date)
        except Term.DoesNotExist:  # no term covers the requested date
            return None
        week_of_term = date.isocalendar()[1] - term.start_date.isocalendar()[1] + 1
        weeks_in_cycle = len(settings.TIMETABLE_WEEKS)
        week = (week_of_term - term.start_week) % weeks_in_cycle + 1
        try:
            return Day.objects.get(day_of_week=date.weekday(), week=week)
        except Day.DoesNotExist:
            return None

    def get_periods(self, date):
        try:  # see if we have a one-off date structure
            #periods = self.get(date=date).periods.all()
            periods = self.get(date=date).periodset.period_set.all()
        except ObjectDoesNotExist:  # otherwise return a default set for that day
            periods = []
        if periods:
            return periods
        else:
            #TODO - what if date does not correlate to entry.day?
            day = self.get_day(date=date)
            if day:
                #return day.periods.all()
                return day.periodset.period_set.all()
            else:
                return None

    def get_period(self, date, period_code):
        periods = self.get_periods(date)
        if periods:
            return periods.get(code=period_code)
        else:
            return None

class Date(models.Model):
    date = models.DateField(unique=True)
    periodset = models.ForeignKey(PeriodSet)
    #periods = models.ManyToManyField(Period, blank=True, null=True)
    objects = DateManager()

    def __unicode__(self):
        return str(self.date.strftime("%d/%m/%y (%a)"))

    def get_period(self, period_code):
        return self.periodset.period_set.get(code=period_code)


    # TODO - this doesn't work as the DB doesn't get committed to until later, and the event.save() call performs a
    # query to get the relevant date back out of the DB. Could re-jig pass the Date object directly perhaps
    def save(self, *args, **kwargs):
        super(Date, self).save(*args, **kwargs)
        for event in Event.objects.filter(date=self.date).exclude(google_event_id__exact=''): # TODO remove exclude
            event.save(date_obj=self)



'''
class Something(models.Model):
    def _get_period_time(self):
        if period time defined:
            return period time
        else
            return standard period time

    period_time = property(_get_full_name)
'''
