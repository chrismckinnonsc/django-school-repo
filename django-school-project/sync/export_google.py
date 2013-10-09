
#DEPRECATED! use google_admin or google_tasks

from school.models import Subject, SchoolClass, Student, StaffMember, Semester

from django.conf import settings
import auth_google
import gdata.apps.service
import gdata.apps.groups.service
import logging,time
logger = logging.getLogger(__name__)

#TODO - re-factor in OO

#TODO - use async task of some sort (celery?)
def sync_group(groups_obj, group_name, new_members, new_owners=False, group_permissions='Member'):
    existing_members = []
    existing_owners = []

    added_members = []
    added_owners = []
    removed_members = []
    removed_owners = []

    #TODO - set group settings to allow all in domain to post, and moderate all non-member posting. This requires the
    #       group settings API and matching OAuth authorisation

    #grab current membership
    try:
        allMembers = groups_obj.RetrieveAllMembers(group_name)
        for m in allMembers:
            existing_members.append(m['memberId'])
        allOwners = groups_obj.RetrieveAllOwners(group_name)
        for o in allOwners:
            existing_owners.append(o['email'])
    except gdata.apps.service.AppsForYourDomainException as err:
        if err.reason == 'EntityDoesNotExist':
            logger.info("group %s does not exist" % group_name)
            groups_obj.CreateGroup(group_name, group_name,
                                   "Generated on %s by %s" % (time.asctime(), settings.PROJECT_NAME ),
                                   group_permissions)
            #TODO check for exceptions

    for member in existing_members:
        if not ((new_members and new_members.filter(email__iexact=member).exists()) or (new_owners and new_owners.filter(email__iexact=member).exists())):
            #TODO - alert, but don't remove non-domain members
            groups_obj.RemoveMemberFromGroup(member, group_name)
            logger.info("removed member %s from %s" % (member, group_name))
            removed_members.append(member)
    if new_owners:
        for owner in existing_owners:
            if not new_owners.filter(email__iexact=owner).exists():
                groups_obj.RemoveOwnerFromGroup(owner, group_name)
                logger.info("removed owner %s from %s" % (owner, group_name))
                removed_owners.append(owner)

    if new_members:
        for new_member in new_members:
            if not new_member.email.lower() in existing_members:
                groups_obj.AddMemberToGroup(new_member.email, group_name)
                logger.info("added member %s to %s" % (new_member, group_name))
                added_members.append(new_member)
            else:
                logger.info("skipping %s for %s - already a member" % (new_member, group_name))
    if new_owners:
        for new_owner in new_owners:
            try:
                if not new_owner.email.lower() in existing_owners:
                    groups_obj.AddOwnerToGroup(new_owner.email, group_name)
                    logger.info("added owner %s to %s" % (new_owner, group_name))
                    added_owners.append(new_owner)
                else:
                    logger.info("skipping %s for %s - already an owner" % (new_owner, group_name))
                if not new_owner.email.lower() in existing_members: #owners need to be members too...
                    groups_obj.AddMemberToGroup(new_owner.email, group_name)
                    logger.info("added member %s to %s" % (new_owner, group_name))
                    added_members.append(new_owner)
                else:
                    logger.info("skipping %s for %s - already a member" % (new_owner, group_name))
            except gdata.apps.service.AppsForYourDomainException as err:
                #TODO parse reason
                logger.error(err)


def update_google_groups(request):
    #TODO - split class/subject from all/year groups
    #TODO - remove old groups
    #TODO - update all-staff group, teaching-staff/ES-staff, faculty groups
    #TODO Mentor groups come from timetable currently - should check if this matches import data

    logger.info("--------- Starting Google Group Sync %s -----------" % time.asctime())

    year = Semester.working(request).year

    groups_obj = gdata.apps.groups.service.GroupsService(domain=settings.GOOGLE_APPS_DOMAIN)
    auth_google.authorize(groups_obj)

    #update all classes in the working cycle
    for cl in SchoolClass.objects.filter(cycle=Semester.working(request)):
        sync_group(groups_obj, cl.code+"-"+year, cl.students.filter(is_current=True), cl.teachers.all(is_current=True))

    #update all subjects with classes in the working cycle
    for sub in Subject.objects.all():
        #get the classes in this subject in the working cycle
        sub_classes = SchoolClass.objects.filter(subject=sub).filter(cycle=Semester.working(request))
        sync_group(groups_obj, sub.code+"-"+year,
                   Student.objects.filter(is_current=True).filter(schoolclass__in=sub_classes),
                   StaffMember.objects.filter(is_current=True).filter(schoolclass__in=sub_classes))

    #update all students group
    sync_group(groups_obj, "students", Student.objects.filter(is_current=True))

    #update year level groups
    for yearlevel in ["10", "11", "12"]:
        sync_group(groups_obj, "year%s-%s" % (yearlevel, year),
                   Student.objects.filter(is_current=True).filter(year_level=year), False)

    #update house groups
    for house in list(set(Student.objects.filter(is_current=True).values_list('house_group', flat=True))):
        sync_group(groups_obj, "%s-House" % house.Name.capitalize(),
                   Student.objects.filter(house_group=house).filter(IsCurrent=True),
                   StaffMember.objects.filter(house_group=house).filter(IsCurrent=True))
        sync_group(groups_obj, "%s-Staff" % house.Name.capitalize(), False,
                   StaffMember.objects.filter(house_group=house).filter(IsCurrent=True))
        sync_group(groups_obj, "%s-Mentors" % house.Name.capitalize(), False,
                   StaffMember.objects.filter(house_group=house).filter(schoolclass__code__startswith="MENT"))

    #group for all mentors
    sync_group(groups_obj, "Mentors", False, StaffMember.objects.filter(schoolclass__code__startswith="MENT"))


def update_google_users(request):
    logger.info("--------- Starting Google User Sync %s -----------" % time.asctime())