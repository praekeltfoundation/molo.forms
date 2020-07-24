CHANGE LOG
==========
10.1.20
-------
- Ensure skip logic recalculates pages based on skipped questions

10.1.19
-------
- Bug fix: forms_list_linked_to_pages template tag was rendering parent forms

10.1.18
-------
- Fix error raised when querying the api for an article that has a form attached

10.1.17
-------
- Update success url's get params suffix

10.1.16
-------
- Add JSON responses for a form success view

10.1.15
-------
- Template tag bug fix, add a check for MoloFormPage instance

10.1.14
-------
- Fix Form submission results page to filter by article_page when present
- Add boolean Molo Form Setting to dynamically add an Article Page field to the forms
- Add Article Form Page's success url
- Update Templates to skip label and help text for hidden fields
- Add model level validation

10.1.13
-------
- Exclude `article_form_only` forms in forms index pages
- Add `article_form_only` flag to `MoloFormPage` model
- Save article_page attribute on form submissions

10.1.9
------
- Add ability for API form submissions to be linked to a user
- User is created/retrieved based on 'uuid' parameter submitted with the form data

10.1.8
------
- Add template filter to add urls as anchor elements on the form's thank you text of the success page

10.1.7
------
- Add support for hidden form fields

10.1.6
------
- Add ArticlePageForms model and forms_list_linked_to_pages template tag to link surveys to articles

10.1.5
------
Updated the README
Small changes to API endpoints
- Remove Personalisable forms from list view
- Prevent submissions to unpublished forms
- Enable filtering by allow_anonymous_submission
- Show input_name attr on form fields in the detail view

10.1.4
------
Add API endpoint that accepts form submissions

10.1.3
------
Add API endpoint to display forms

10.1.2
------
Fix skip logic's checkbox issue

10.1.1
------
Fix pagination on forms submission

10.1.0
------
Oficial release for Django 2.2.5+ support

10.0.1
------
Fix SkipLogicStreamBlock's media block

10.0.0
------
Molo Version 10 support

9.1.0
-----
Add folder structure to form's index page

9.0.1
-----
Checkbox bug fix

9.0.0
-----
Initial release
