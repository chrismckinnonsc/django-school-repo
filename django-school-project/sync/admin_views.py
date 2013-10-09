from django.shortcuts import  render
from django.http import HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sites.models import Site

import gdata.gauth
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

import import_data, export_mds, google_admin, export_realsmart, export_ldap, google_tasks
from sync_form import *

#flow = None

def sync(request):
    if request.method == 'POST':
        import_students_form = ImportStudentsForm(request.POST, request.FILES) # A form bound to the POST data
        import_staff_form = ImportStaffForm(request.POST, request.FILES) # A form bound to the POST data
        import_enrolments_form = ImportEnrolmentsForm(request.POST,request.FILES)
        generate_mds_file_form = GenerateMDSFileForm(request.POST)
        update_realsmart_form = UpdateRealSmartForm(request.POST)
        update_ad_groups_form = UpdateADGroupsForm(request.POST)
        update_authcate_form = UpdateAuthcateForm(request.POST)
        update_google_groups_form = UpdateGoogleGroupsForm(request.POST)
        update_google_students_form = UpdateGoogleStudentsForm(request.POST)
        google_access_token_form = GoogleAccessTokenForm(request.POST)


        if import_students_form.is_valid(): # All validation rules pass
            import_data.import_students(request.FILES['students_file'])
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST
        elif import_staff_form.is_valid(): # All validation rules pass
            import_data.import_staff(request.FILES['staff_file'])
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST
        elif import_enrolments_form.is_valid():
            import_data.import_enrolments_from(request.FILES['enrolments_file'], request=request)
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST

        elif request.POST.has_key("update_google_groups"):
            google_tasks.update_google_groups_all_classes(request)
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST
        elif request.POST.has_key("update_google_students"):
            if not 'google_sync' in request.session:
                request.session['google_sync'] = google_admin.GoogleSync(request)
            request.session['google_sync'].update_google_students(request)
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST

        elif request.POST.has_key("generate_mds"):
            export_mds.export_mds()
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST

        elif request.POST.has_key("update_realsmart"):
            export_realsmart.export_realsmart(request)
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST

        elif request.POST.has_key("update_ad_groups"):
            export_ldap.sync_groups(request)
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST

        elif request.POST.has_key("update_authcate"):
            import_data.import_authcate_from_ldap()
            return HttpResponseRedirect('/admin/sync/') # Redirect after POST
    else:
        import_students_form = ImportStudentsForm()
        import_staff_form = ImportStaffForm()
        import_enrolments_form = ImportEnrolmentsForm()
        generate_mds_file_form = GenerateMDSFileForm()
        update_realsmart_form = UpdateRealSmartForm()
        update_ad_groups_form = UpdateADGroupsForm()
        update_authcate_form = UpdateAuthcateForm()
        update_google_groups_form = UpdateGoogleGroupsForm()
        update_google_students_form = UpdateGoogleStudentsForm()
        google_access_token_form = GoogleAccessTokenForm()
        if request.GET.has_key("generate_google_access_token"):
            return google_admin.oauth_step_1(request=request)


    return render(request, 'admin/sync.html', {
        'import_students_form': import_students_form,
        'import_staff_form': import_staff_form,
        'import_enrolments_form': import_enrolments_form,
        'generate_mds_file_form': generate_mds_file_form,
        'update_realsmart_form': update_realsmart_form,
        'update_ad_groups_form': update_ad_groups_form,
        'update_authcate_form': update_authcate_form,
        'update_google_groups_form': update_google_groups_form,
        'update_google_students_form': update_google_students_form,
        'google_access_token_form': google_access_token_form,
        })
#    return render_to_response("admin/sync.html",
#        context_instance=RequestContext(request,{}))

def token(request):
    code = request.GET.get('code')
    google_admin.oauth_step_2(code)
    return HttpResponseRedirect('/admin/sync/') # Redirect after POST


sync = staff_member_required(sync)
