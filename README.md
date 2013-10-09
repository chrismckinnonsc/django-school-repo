*django-school* is a project to create a school database using django. I will probably split the individual apps into
separate repositories eventually. At the moment the following apps are included:
* school - the basic school structure, including models for students, staff, subjects, classes, faculties, and
relationships between these
* timetable - models for a school timetable, dependent on school
* sync - modules and functions to import and export data across a variety of sources and sinks.

This was initially developed for John Monash Science School (JMSS). While the models were created for JMSS, I tried to
keep things as general as possible. Certain import/export functionality will only make sense for certain types of
schools - the basic staff and student imports are from CSV files generated by the CASES/CASES21 system used by
Victorian Government schools. Other sync functionality relates to other systems JMSS use e.g. Monash University,
RealSmart, Timetabler and Google Apps for Education.