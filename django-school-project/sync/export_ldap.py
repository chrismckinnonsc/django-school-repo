import ldap
from school.models import *

STUDENT_BASE = 'CN=%s,OU=Student,OU=Accounts,DC=YOUR,DC=DOMAIN,DC=EDU'
STAFF_BASE = 'CN=%s,OU=Staff,OU=Accounts,DC=YOUR,DC=DOMAIN,DC=EDU'

STUDENT_GROUP = 'Students'
STAFF_GROUP = 'Staff'


def sync_group(base_dn, group_name, user_model, server='ldap://your.domain.edu', username='', password=''):
    '''
    Populates an AD group with objects from the specified user model.
    Designed for AD, but should work with most LDAP systems with a little tweaking

    Usage:
    from school.models import Student, StaffMember
    sync_group(STUDENT_BASE, STUDENT_GROUP, Student, password='foobar')
    sync_group(STAFF_BASE, STAFF_GROUP, StaffMember, password='foobar')
    '''
    c = ldap.initialize(server)

    #these options seem to be required for AD
    c.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
    c.set_option(ldap.OPT_REFERRALS, 0)

    #bind with someone authorized to manage the group
    c.simple_bind_s(username, password)

    #find the group to modify
    dn,e = c.search_s('dc=your,dc=domain,dc=edu',ldap.SCOPE_SUBTREE,'(sAMAccountName=%s)' % group_name)[0]

    #TODO - create group if it doesn't exist

    dn_current, e_current = c.search_s(dn, ldap.SCOPE_BASE)[0]
    try:
        current_members = e_current['member']
    except KeyError:
        current_members = []

    #set up the mod attributes
    modattr = []
    for s in user_model.objects.filter(is_current=True):
        if s.network_id:
            new_dn=str(base_dn % s.network_id)
            if new_dn in current_members:
                continue
            modattr.append((ldap.MOD_ADD,'member',new_dn))

    if modattr:
        c.modify_s(dn,modattr)


#TODO - populate this
def sync_groups(request=None):
    pass
