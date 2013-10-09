from django import forms

class ImportStudentsForm(forms.Form):
    students_file = forms.FileField()

class ImportStaffForm(forms.Form):
    staff_file = forms.FileField()

class ImportEnrolmentsForm(forms.Form):
    #TODO - add cycle to import into
    enrolments_file = forms.FileField()

class GenerateMDSFileForm(forms.Form):
    pass

class UpdateADGroupsForm(forms.Form):
    pass

class UpdateAuthcateForm(forms.Form):
    pass

class UpdateRealSmartForm(forms.Form):
    pass

class UpdateGoogleGroupsForm(forms.Form):
    pass

class UpdateGoogleStudentsForm(forms.Form):
    #TODO - add option to disable accounts not in file
    pass

class GoogleAccessTokenForm(forms.Form):
    pass
    #client_id=forms.CharField(max_length=100)
    #client_secret=forms.CharField(max_length=100)
